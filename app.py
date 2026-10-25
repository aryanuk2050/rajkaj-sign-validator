import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
import re
import io
import zipfile
import base64
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="Smart Office & DSC Toolkit", page_icon="✅", layout="centered")
st.title("✅ स्मार्ट ऑफिस एवं डिजिटल सिग्नेचर टूलकिट")
st.caption("राजकाज, ई-आधार व सभी प्रमाण पत्रों के लिए ऑल-इन-वन पीडीएफ सॉल्यूशन")

# -------------------- HELPER FUNCTIONS --------------------

def extract_signer_from_pdf_bytes(doc, xref):
    info = {
        "name": "", "designation": "", "location": "", "date": "", "reason": "",
        "issuer": "", "serial": "", "valid_from": "", "valid_to": ""
    }
    try:
        sig_obj_str = doc.xref_object(xref)
        
        reason_match = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
        if reason_match and reason_match.group(1).strip():
            info["reason"] = reason_match.group(1).strip()
            
        loc_match = re.search(r'/Location\s*\((.*?)\)', sig_obj_str)
        if loc_match and loc_match.group(1).strip():
            info["location"] = loc_match.group(1).strip()
            
        date_match = re.search(r'/M\s*\(D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', sig_obj_str)
        if date_match:
            y, m, d, hh, mm, ss = date_match.groups()
            info["date"] = f"{y}.{m}.{d} {hh}:{mm}:{ss} IST"
            
        name_match = re.search(r'/Name\s*\((.*?)\)', sig_obj_str)
        if name_match:
            info["name"] = name_match.group(1).strip()

        contents_match = re.search(r'/Contents\s*<([0-9A-Fa-f\s]+)>', sig_obj_str)
        if contents_match:
            hex_data = re.sub(r'\s+', '', contents_match.group(1)).rstrip('0')
            if len(hex_data) % 2 != 0:
                hex_data += '0'
            der_bytes = bytes.fromhex(hex_data)
            certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
            if certs:
                cert = certs[0]
                info["serial"] = str(cert.serial_number)
                try:
                    info["valid_from"] = str(cert.not_valid_before_utc.date())
                    info["valid_to"] = str(cert.not_valid_after_utc.date())
                except Exception:
                    info["valid_from"] = str(cert.not_valid_before.date())
                    info["valid_to"] = str(cert.not_valid_after.date())

                for attr in cert.issuer:
                    if attr.oid == x509.NameOID.COMMON_NAME:
                        info["issuer"] = attr.value

                for attr in cert.subject:
                    if attr.oid == x509.NameOID.COMMON_NAME and not info["name"]:
                        info["name"] = attr.value
                    elif attr.oid in (x509.NameOID.TITLE, x509.NameOID.ORGANIZATIONAL_UNIT_NAME, x509.NameOID.ORGANIZATION_NAME):
                        if not info["designation"]:
                            info["designation"] = attr.value
    except Exception:
        pass
    return info

def draw_exact_tick_polygon(shape, pts, fill_color, stroke_color=None, stroke_width=1.0):
    shape.draw_quad(fitz.Quad(pts[0], pts[1], pts[5], pts[2]))
    shape.draw_quad(fitz.Quad(pts[2], pts[3], pts[5], pts[4]))
    shape.finish(color=fill_color, fill=fill_color, width=0)

    if stroke_color and stroke_width > 0:
        for i in range(6):
            shape.draw_line(pts[i], pts[(i + 1) % 6])
        shape.finish(color=stroke_color, width=stroke_width, lineCap=0, lineJoin=0)

def draw_green_tick_and_text(page, rect, name, designation, date_str, reason):
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    
    w, h = rect.width, rect.height
    x0, y0 = rect.x0, rect.y0

    t_left = 0.032
    t_right = 0.039

    pts_main = [
        fitz.Point(x0 + w * 0.310, y0 + h * 0.585),
        fitz.Point(x0 + w * (0.310 + t_left), y0 + h * 0.505),
        fitz.Point(x0 + w * 0.435, y0 + h * 0.720),
        fitz.Point(x0 + w * 0.595, y0 + h * 0.190),
        fitz.Point(x0 + w * (0.595 + t_right), y0 + h * 0.260),
        fitz.Point(x0 + w * 0.445, y0 + h * 0.875),
    ]
    
    dx = max(w * 0.011, 1.1)
    dy = max(h * 0.017, 1.1)
    pts_shadow = [fitz.Point(p.x + dx, p.y + dy) for p in pts_main]

    shape = page.new_shape()
    draw_exact_tick_polygon(shape, pts_shadow, fill_color=(0, 0, 0), stroke_color=None)

    border_w = max(w * 0.0055, 0.7)
    draw_exact_tick_polygon(
        shape, 
        pts_main, 
        fill_color=(0.0, 0.65, 0.16),
        stroke_color=(0, 0, 0), 
        stroke_width=border_w
    )
    shape.commit()
    
    header_fontsize = h * 0.215
    body_fontsize = h * 0.108
    
    page.insert_text(
        fitz.Point(x0 + 2, y0 + h * 0.23),
        "Signature valid",
        fontsize=header_fontsize,
        fontname="helv",
        color=(0, 0, 0)
    )
    
    raw_lines = [f"Digitally signed by {name}"]
    if designation:
        for d_line in designation.splitlines():
            if d_line.strip():
                raw_lines.append(d_line.strip())
    if date_str:
        raw_lines.append(f"Date: {date_str}")
    if reason:
        raw_lines.append(f"Reason: {reason}")
        
    start_y = y0 + h * 0.395
    line_gap = body_fontsize * 1.18
    for i, line in enumerate(raw_lines):
        page.insert_text(
            fitz.Point(x0 + 2, start_y + i * line_gap),
            line,
            fontsize=body_fontsize,
            fontname="helv",
            color=(0, 0, 0)
        )

def render_share_and_print_buttons(pdf_bytes, filename):
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    html_code = f"""
    <div style="display: flex; gap: 10px; flex-direction: column; margin-top: 5px;">
        <button onclick="sharePDF()" style="
            width: 100%; padding: 12px; background-color: #25D366; color: white;
            border: none; border-radius: 8px; font-size: 16px; font-weight: bold;
            cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
            📤 कहीं भी शेयर करें (WhatsApp / Telegram / Mail)
        </button>
        <button onclick="printPDF()" style="
            width: 100%; padding: 12px; background-color: #0066CC; color: white;
            border: none; border-radius: 8px; font-size: 16px; font-weight: bold;
            cursor: pointer; box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
            🖨️ सीधे प्रिंट करें (Direct Print)
        </button>
    </div>
    <script>
    function getBlob() {{
        const b64Data = "{b64_pdf}";
        const byteCharacters = atob(b64Data);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {{
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }}
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], {{ type: "application/pdf" }});
    }}

    async function sharePDF() {{
        const blob = getBlob();
        const file = new File([blob], "{filename}", {{ type: "application/pdf" }});
        if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
            try {{
                await navigator.share({{
                    files: [file],
                    title: "{filename}",
                    text: "वैलिडेटेड दस्तावेज़"
                }});
            }} catch (err) {{
                console.log("Share cancelled", err);
            }}
        }} else {{
            alert("आपके ब्राउज़र में डायरेक्ट शेयर सपोर्ट नहीं है, कृपया ऊपर दिए गए डाउनलोड बटन से सेव करके शेयर करें।");
        }}
    }}

    function printPDF() {{
        const blob = getBlob();
        const blobUrl = URL.createObjectURL(blob);
        const printWindow = window.open(blobUrl, '_blank');
        if (printWindow) {{
            printWindow.onload = function() {{
                printWindow.focus();
                printWindow.print();
            }};
        }} else {{
            alert("कृपया ब्राउज़र में Pop-up allow करें या फाइल डाउनलोड करके प्रिंट करें।");
        }}
    }}
    </script>
    """
    components.html(html_code, height=120)

# -------------------- MAIN TABS --------------------

tab1, tab2, tab3, tab4 = st.tabs([
    "✅ सिंगल वैलिडेटर", 
    "📚 बल्क (Bulk) वैलिडेटर", 
    "📉 कॉम्प्रेस व मर्ज", 
    "🪪 कार्ड क्रॉपर व स्टैम्प"
])

# ==================== TAB 1: SINGLE VALIDATOR ====================
with tab1:
    uploaded_file = st.file_uploader("यहाँ कोई भी PDF फाइल चुनें (राजकाज / ई-आधार / प्रमाण पत्र)", type=["pdf"], key="single_pdf")

    if uploaded_file:
        pdf_bytes = uploaded_file.read()
        doc = fitz.open("pdf", pdf_bytes)
        
        unlocked = True
        if doc.needs_pass:
            unlocked = False
            pwd = st.text_input("🔒 यह PDF पासवर्ड से सुरक्षित है। कृपया पासवर्ड दर्ज करें:", type="password")
            if pwd:
                if doc.authenticate(pwd):
                    st.success("🔓 पासवर्ड सही है! फाइल अनलॉक हो गई।")
                    unlocked = True
                else:
                    st.error("❌ गलत पासवर्ड! कृपया सही पासवर्ड डालें।")

        if unlocked:
            default_info = {
                "name": "Subhash Maharia", 
                "designation": "Designation : Electoral Registration\nOfficer", 
                "date": "2026.10.01 14:07:22 IST", 
                "reason": "Approved",
                "issuer": "NIC / eMudhra CA", "serial": "N/A", "valid_from": "N/A", "valid_to": "N/A"
            }
            
            for page in doc:
                for widget in page.widgets():
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        extracted = extract_signer_from_pdf_bytes(doc, widget.xref)
                        if extracted.get("name"):
                            default_info["name"] = extracted["name"]
                        if extracted.get("designation"):
                            default_info["designation"] = f"Designation : {extracted['designation']}"
                        elif extracted.get("location"):
                            default_info["designation"] = f"Location: {extracted['location']}"
                        if extracted.get("date"):
                            default_info["date"] = extracted["date"]
                        if extracted.get("reason"):
                            default_info["reason"] = extracted["reason"]
                        for k in ("issuer", "serial", "valid_from", "valid_to"):
                            if extracted.get(k):
                                default_info[k] = extracted[k]

            with st.expander("🔍 डिजिटल सर्टिफिकेट की तकनीकी जानकारी (Certificate Inspector)"):
                st.write(f"**जारीकर्ता (Issuer CA):** {default_info['issuer']}")
                st.write(f"**सर्टिफिकेट सीरियल नंबर:** `{default_info['serial']}`")
                st.write(f"**वैधता अवधि (Validity):** {default_info['valid_from']} से {default_info['valid_to']} तक")

            st.subheader("सिग्नेचर विवरण:")
            name = st.text_input("हस्ताक्षरकर्ता / विभाग (Digitally signed by):", value=default_info["name"])
            designation = st.text_area("पद / विवरण (दूसरी लाइन के लिए Enter दबाएं):", value=default_info["designation"], height=68)
            date_str = st.text_input("दिनांक व समय (Date):", value=default_info["date"])
            reason = st.text_input("कारण (Reason - यदि खाली रखना हो तो मिटा दें):", value=default_info["reason"])

            if st.button("🚀 ग्रीन टिक (✔) लागू करें और PDF तैयार करें", use_container_width=True):
                out_doc = fitz.open("pdf", doc.tobytes())
                stamped_count = 0
                for page in out_doc:
                    widgets = list(page.widgets())
                    for widget in widgets:
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            rect = widget.rect
                            page.delete_widget(widget)
                            draw_green_tick_and_text(page, rect, name, designation, date_str, reason)
                            stamped_count += 1
                            
                if stamped_count == 0:
                    last_page = out_doc[-1]
                    pw, ph = last_page.rect.width, last_page.rect.height
                    custom_rect = fitz.Rect(pw - 220, ph - 110, pw - 30, ph - 30)
                    draw_green_tick_and_text(last_page, custom_rect, name, designation, date_str, reason)

                st.session_state["processed_pdf"] = out_doc.tobytes()
                st.session_state["show_preview"] = False
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["default_filename"] = f"{base_name}_Validated"

            if "processed_pdf" in st.session_state:
                st.success("✅ आपकी ग्रीन टिक वाली फाइल तैयार है!")
                
                if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True):
                    st.session_state["show_preview"] = not st.session_state.get("show_preview", False)
                    
                if st.session_state.get("show_preview", False):
                    st.info("📄 फाइल का प्रीव्यू (ज़ूम करके देख सकते हैं):")
                    preview_doc = fitz.open("pdf", st.session_state["processed_pdf"])
                    for i, page in enumerate(preview_doc):
                        pix = page.get_pixmap(dpi=150)
                        st.image(pix.tobytes("png"), caption=f"पेज {i+1}", use_container_width=True)

                st.divider()

                custom_name = st.text_input(
                    "✏️ फाइल को नया नाम दें (Rename File):", 
                    value=st.session_state.get("default_filename", "Validated_Document")
                )
                final_filename = custom_name.strip()
                if not final_filename.lower().endswith(".pdf"):
                    final_filename += ".pdf"

                st.download_button(
                    label=f"📥 फाइल सेव / डाउनलोड करें ({final_filename})",
                    data=st.session_state["processed_pdf"],
                    file_name=final_filename,
                    mime="application/pdf",
                    use_container_width=True
                )

                render_share_and_print_buttons(st.session_state["processed_pdf"], final_filename)

# ==================== TAB 2: BULK VALIDATOR ====================
with tab2:
    st.subheader("📚 एक साथ कई PDF फाइलों में ग्रीन टिक लगाएं")
    st.write("राजकाज के कई आदेशों या प्रमाण पत्रों को एक साथ सिलेक्ट करें। यह अपने आप सबका डेटा पढ़कर ग्रीन टिक लगा देगा और एक ZIP फाइल बना देगा।")
    
    bulk_files = st.file_uploader("यहाँ एक या अधिक PDF फाइलें चुनें", type=["pdf"], accept_multiple_files=True, key="bulk_pdf")
    
    if bulk_files:
        if st.button(f"⚡ सभी {len(bulk_files)} फाइलों को एक साथ वैलिडेट करें", use_container_width=True):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for bf in bulk_files:
                    b_doc = fitz.open("pdf", bf.read())
                    if b_doc.needs_pass:
                        continue
                    for page in b_doc:
                        widgets = list(page.widgets())
                        for widget in widgets:
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                                ext = extract_signer_from_pdf_bytes(b_doc, widget.xref)
                                b_name = ext.get("name") or "Authorized Signatory"
                                b_desig = f"Designation : {ext['designation']}" if ext.get("designation") else (f"Location: {ext['location']}" if ext.get("location") else "")
                                b_date = ext.get("date") or ""
                                b_reason = ext.get("reason") or "Approved"
                                rect = widget.rect
                                page.delete_widget(widget)
                                draw_green_tick_and_text(page, rect, b_name, b_desig, b_date, b_reason)
                    clean_name = bf.name.rsplit(".", 1)[0] + "_Validated.pdf"
                    zf.writestr(clean_name, b_doc.tobytes())
            
            st.success(f"✅ सभी {len(bulk_files)} फाइलें सफलतापूर्वक वैलिडेट हो गईं!")
            st.download_button(
                label="📦 सभी वैलिडेटेड फाइलें डाउनलोड करें (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="All_Validated_Documents.zip",
                mime="application/zip",
                use_container_width=True
            )

# ==================== TAB 3: COMPRESS & MERGE ====================
with tab3:
    st.subheader("📉 1. पीडीएफ साइज कम करें (PDF Size Compressor)")
    st.caption("राजकाज या SSO पोर्टल पर अपलोड करने के लिए बड़ी PDF को छोटा करें।")
    comp_file = st.file_uploader("कॉम्प्रेस करने के लिए PDF चुनें", type=["pdf"], key="comp_pdf")
    
    if comp_file:
        orig_bytes = comp_file.read()
        orig_kb = len(orig_bytes) / 1024
        st.info(f"वर्तमान फाइल साइज: **{orig_kb:.1f} KB**")
        
        comp_mode = st.radio("कॉम्प्रेशन लेवल चुनें:", [
            "लाइट कॉम्प्रेशन (टेक्स्ट एकदम शार्प रहेगा)",
            "हाई कॉम्प्रेशन (स्कैन की गई बड़ी फाइलों के लिए - 100 DPI)"
        ])
        
        if st.button("📉 साइज कम करें (Compress PDF)", use_container_width=True):
            c_doc = fitz.open("pdf", orig_bytes)
            if "लाइट" in comp_mode:
                comp_bytes = c_doc.tobytes(garbage=4, deflate=True, clean=True)
            else:
                new_doc = fitz.open()
                for page in c_doc:
                    pix = page.get_pixmap(dpi=100)
                    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                    new_page.insert_image(page.rect, stream=pix.tobytes("jpeg"))
                comp_bytes = new_doc.tobytes(garbage=4, deflate=True)
                
            new_kb = len(comp_bytes) / 1024
            st.success(f"✅ नया साइज: **{new_kb:.1f} KB** (पहले {orig_kb:.1f} KB था)")
            st.download_button(
                label="📥 कॉम्प्रेस की गई PDF डाउनलोड करें",
                data=comp_bytes,
                file_name="Compressed_" + comp_file.name,
                mime="application/pdf",
                use_container_width=True
            )

    st.divider()
    st.subheader("📑 2. दो या अधिक PDF को जोड़ें (Merge PDFs)")
    merge_files = st.file_uploader("जोड़ने के लिए 2 या अधिक PDF फाइलें चुनें", type=["pdf"], accept_multiple_files=True, key="merge_pdf")
    if merge_files and len(merge_files) >= 2:
        if st.button("🔗 सभी फाइलों को जोड़कर एक PDF बनाएं", use_container_width=True):
            merged_doc = fitz.open()
            for mf in merge_files:
                m_doc = fitz.open("pdf", mf.read())
                merged_doc.insert_pdf(m_doc)
            merged_bytes = merged_doc.tobytes(garbage=3, deflate=True)
            st.success("✅ सभी फाइलें जुड़ चुकी हैं!")
            st.download_button(
                label="📥 मर्ज की गई PDF डाउनलोड करें",
                data=merged_bytes,
                file_name="Merged_Document.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ==================== TAB 4: ID CARD CROPPER & OFFICE STAMP ====================
with tab4:
    st.subheader("🪪 1. पीवीसी कार्ड क्रॉपर (e-Aadhaar / Jan-Aadhaar Card Size)")
    st.caption("A4 साइज के दस्तावेज़ से केवल नीचे वाला कार्ड हिस्सा काटकर अलग करें (और सिग्नेचर पर ग्रीन टिक भी लगाएं)।")
    card_file = st.file_uploader("कार्ड क्रॉप करने के लिए PDF चुनें", type=["pdf"], key="card_pdf")
    
    if card_file:
        c_bytes = card_file.read()
        c_doc = fitz.open("pdf", c_bytes)
        pwd_ok = True
        if c_doc.needs_pass:
            pwd_ok = False
            c_pwd = st.text_input("🔒 पासवर्ड दर्ज करें:", type="password", key="card_pwd")
            if c_pwd and c_doc.authenticate(c_pwd):
                pwd_ok = True

        if pwd_ok:
            crop_ratio = st.slider("नीचे से कार्ड की ऊंचाई का हिस्सा चुनें (%):", 20, 50, 31)
            auto_tick = st.checkbox("कार्ड पर मौजूद डिजिटल सिग्नेचर (?) को भी ग्रीन टिक (✔) में बदलें", value=True)
            
            if st.button("✂️ कार्ड क्रॉप करें और प्रीव्यू देखें", use_container_width=True):
                # 1. यदि कार्ड पर सिग्नेचर है तो उस पर भी ग्रीन टिक लगा दें
                if auto_tick:
                    for page in c_doc:
                        for widget in list(page.widgets()):
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                                ext = extract_signer_from_pdf_bytes(c_doc, widget.xref)
                                s_name = ext.get("name") or "Unique Identification Authority of India"
                                s_desig = f"Location: {ext['location']}" if ext.get("location") else (f"Designation : {ext['designation']}" if ext.get("designation") else "")
                                s_date = ext.get("date") or ""
                                s_reason = ext.get("reason") or ""
                                rect = widget.rect
                                page.delete_widget(widget)
                                draw_green_tick_and_text(page, rect, s_name, s_desig, s_date, s_reason)

                # 2. बिना किसी एरर के सुरक्षित तरीके से कार्ड क्रॉप करना
                page = c_doc[0]
                r = page.rect
                top_y = r.y0 + r.height * (1.0 - (crop_ratio / 100.0))
                crop_rect = fitz.Rect(r.x0 + 12, top_y, r.x1 - 12, r.y1 - 10)
                
                # केवल क्लिप किए गए हिस्से का हाई-क्वालिटी प्रीव्यू दिखाना
                pix = page.get_pixmap(dpi=200, clip=crop_rect)
                st.image(pix.tobytes("png"), caption="क्रॉप किया गया पीवीसी कार्ड", use_container_width=True)
                
                # पेज का CropBox सेट करके सीधे नई PDF सेव करना (इससे ValueError कभी नहीं आएगा)
                page.set_cropbox(crop_rect)
                out_card = fitz.open()
                out_card.insert_pdf(c_doc, from_page=0, to_page=0)
                
                st.download_button(
                    label="📥 PVC कार्ड PDF डाउनलोड करें",
                    data=out_card.tobytes(),
                    file_name="Card_" + card_file.name,
                    mime="application/pdf",
                    use_container_width=True
                )

    st.divider()
    st.subheader("💮 2. सरकारी ऑफिस स्टैम्प / मुहर लगाएं (Office Stamp)")
    stamp_file = st.file_uploader("मुहर लगाने के लिए PDF चुनें", type=["pdf"], key="stamp_pdf")
    if stamp_file:
        stamp_text = st.selectbox("मुहर का प्रकार चुनें:", [
            "APPROVED / अनुमोदित",
            "MOST URGENT / अति आवश्यक",
            "TRUE COPY / प्रमाणित प्रतिलिपि",
            "SEEN & FILED / देखा गया"
        ])
        stamp_color_choice = st.radio("मुहर का रंग:", ["लाल (Red)", "नीला (Blue)", "हरा (Green)"], horizontal=True)
        color_map = {"लाल (Red)": (0.8, 0.0, 0.0), "नीला (Blue)": (0.0, 0.2, 0.75), "हरा (Green)": (0.0, 0.55, 0.15)}
        s_color = color_map[stamp_color_choice]

        if st.button("💮 पहले पेज पर ऊपरी दाएं कोने में मुहर लगाएं", use_container_width=True):
            s_doc = fitz.open("pdf", stamp_file.read())
            f_page = s_doc[0]
            pw = f_page.rect.width
            s_rect = fitz.Rect(pw - 190, 25, pw - 25, 60)
            
            f_page.draw_rect(s_rect, color=s_color, width=2.0)
            f_page.insert_textbox(s_rect, stamp_text.split("/")[0].strip(), fontsize=13, fontname="helv", color=s_color, align=1)
            
            st.success("✅ मुहर लग चुकी है!")
            st.download_button(
                label="📥 स्टैम्प लगी हुई PDF डाउनलोड करें",
                data=s_doc.tobytes(),
                file_name="Stamped_" + stamp_file.name,
                mime="application/pdf",
                use_container_width=True
            )
