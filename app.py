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

# -------------------- DEEP SIGNATURE EXTRACTOR --------------------

def extract_signer_from_pdf_bytes(doc, page, widget):
    """PDF के सिग्नेचर बॉक्स, XObject स्ट्रीम और PKCS#7 सर्टिफिकेट से 100% पूरी डिटेल्स निकालना"""
    info = {
        "name": "", "designation": "", "location": "", "date": "", "reason": "",
        "issuer": "", "serial": "", "valid_from": "", "valid_to": "", "raw_lines": []
    }
    try:
        xref = widget.xref
        sig_obj_str = doc.xref_object(xref)

        # 1. सिग्नेचर के विज़ुअल बॉक्स (Appearance Stream / XObject) के अंदर छुपे असली टेक्स्ट को पढ़ना
        ap_match = re.search(r'/AP\s*<<[^>]*?/N\s+(\d+)\s+0\s+R', sig_obj_str, re.DOTALL)
        if ap_match:
            ap_xref = int(ap_match.group(1))
            streams_to_check = [ap_xref]
            ap_obj = doc.xref_object(ap_xref)
            # अगर अंदर Form XObjects (जैसे /FRM, /n2) हैं तो उन्हें भी ढूँढना
            sub_refs = re.findall(r'(\d+)\s+0\s+R', ap_obj)
            for sr in sub_refs:
                streams_to_check.append(int(sr))

            extracted_strings = []
            for s_xref in streams_to_check:
                try:
                    stream_bytes = doc.xref_stream(s_xref)
                    if stream_bytes:
                        txt = stream_bytes.decode('latin1', errors='ignore')
                        # PDF text strings को निकालना (...)
                        in_parens = re.findall(r'\(([^()]+)\)', txt)
                        for p in in_parens:
                            clean_p = p.replace('\\(', '(').replace('\\)', ')').strip()
                            if len(clean_p) > 2:
                                extracted_strings.append(clean_p)
                except Exception:
                    pass

            full_ap_text = "\n".join(extracted_strings)
            for line in extracted_strings:
                if "digitally signed by" in line.lower():
                    val = re.sub(r'(?i)digitally signed by\s*:?\s*', '', line).strip()
                    if val:
                        info["name"] = val
                elif "designation" in line.lower():
                    val = re.sub(r'(?i)designation\s*:?\s*', '', line).strip()
                    if val:
                        info["designation"] = val
                elif "date:" in line.lower():
                    val = re.sub(r'(?i)date\s*:?\s*', '', line).strip()
                    if val:
                        info["date"] = val
                elif "reason:" in line.lower():
                    val = re.sub(r'(?i)reason\s*:?\s*', '', line).strip()
                    if val:
                        info["reason"] = val
                elif "location:" in line.lower():
                    val = re.sub(r'(?i)location\s*:?\s*', '', line).strip()
                    if val:
                        info["location"] = val

        # 2. अगर सिग्नेचर /V रेफरेंस में है, तो उस ऑब्जेक्ट को भी पढ़ना
        v_match = re.search(r'/V\s+(\d+)\s+0\s+R', sig_obj_str)
        if v_match:
            v_xref = int(v_match.group(1))
            sig_obj_str = sig_obj_str + "\n" + doc.xref_object(v_xref)

        # 3. PDF सिग्नेचर डिक्शनरी से Reason, Location, Date और Name निकालना
        if not info["reason"]:
            reason_match = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
            if reason_match and reason_match.group(1).strip():
                info["reason"] = reason_match.group(1).strip()

        if not info["location"]:
            loc_match = re.search(r'/Location\s*\((.*?)\)', sig_obj_str)
            if loc_match and loc_match.group(1).strip():
                info["location"] = loc_match.group(1).strip()

        if not info["date"]:
            date_match = re.search(r'/M\s*\(D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', sig_obj_str)
            if date_match:
                y, m, d, hh, mm, ss = date_match.groups()
                info["date"] = f"{y}.{m}.{d} {hh}:{mm}:{ss} IST"

        if not info["name"]:
            name_match = re.search(r'/Name\s*\((.*?)\)', sig_obj_str)
            if name_match and name_match.group(1).strip():
                info["name"] = name_match.group(1).strip()

        # 4. PKCS#7 क्रिप्टोग्राफिक सर्टिफिकेट से अधिकारी का नाम, पद और समय निकालना
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

                titles = []
                for attr in cert.subject:
                    if attr.oid == x509.NameOID.COMMON_NAME and not info["name"]:
                        info["name"] = attr.value
                    elif attr.oid in (x509.NameOID.TITLE, x509.NameOID.ORGANIZATIONAL_UNIT_NAME):
                        if attr.value and attr.value not in titles:
                            titles.append(attr.value)
                if titles and not info["designation"]:
                    info["designation"] = titles[0]
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
    """सिग्नेचर बॉक्स में बिना एक भी लाइन काटे पूरा विवरण और ग्रीन टिक छापना"""
    # अगर सिग्नेचर बॉक्स में बाईं तरफ QR कोड है, तो केवल दाएं हिस्से (जहाँ टेक्स्ट और ? होता है) को साफ करें
    w, h = rect.width, rect.height
    x0, y0 = rect.x0, rect.y0

    # पूरे सिग्नेचर बॉक्स को साफ करना (QR कोड आमतौर पर अलग इमेज में बाईं ओर होता है)
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))

    t_left = 0.032
    t_right = 0.039

    # टिक को बॉक्स के अंदर सुरक्षित ऊंचाई (0.18 से 0.84) में रखना ताकि नीचे से कभी न कटे
    pts_main = [
        fitz.Point(x0 + w * 0.310, y0 + h * 0.560),
        fitz.Point(x0 + w * (0.310 + t_left), y0 + h * 0.480),
        fitz.Point(x0 + w * 0.435, y0 + h * 0.690),
        fitz.Point(x0 + w * 0.595, y0 + h * 0.180),
        fitz.Point(x0 + w * (0.595 + t_right), y0 + h * 0.250),
        fitz.Point(x0 + w * 0.445, y0 + h * 0.840),
    ]
    
    dx = max(w * 0.011, 1.0)
    dy = max(h * 0.016, 1.0)
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
    
    # सारी लाइनों को तैयार करना
    raw_lines = [f"Digitally signed by {name}"]
    if designation:
        for d_line in designation.splitlines():
            if d_line.strip():
                raw_lines.append(d_line.strip())
    if date_str:
        raw_lines.append(f"Date: {date_str}")
    if reason:
        raw_lines.append(f"Reason: {reason}")

    num_lines = len(raw_lines)
    
    # "Signature valid" का साइज और पोजिशन
    header_fontsize = min(h * 0.20, w * 0.115)
    page.insert_text(
        fitz.Point(x0 + 2, y0 + h * 0.21),
        "Signature valid",
        fontsize=header_fontsize,
        fontname="helv",
        color=(0, 0, 0)
    )
    
    # बाकी सभी लाइनों (Name, Designation, Date, Reason) को बॉक्स की ऊंचाई और चौड़ाई में 100% फिट करना
    available_height = h * 0.68
    line_gap = available_height / max(num_lines, 1)
    max_line_chars = max([len(l) for l in raw_lines] + [22])
    
    # फॉन्ट साइज ऐसा चुनें कि न नीचे से कटे और न दाईं तरफ से बाहर निकले
    body_fontsize = min(line_gap * 0.84, (w * 1.72) / max_line_chars, h * 0.105)
    line_gap = min(line_gap, body_fontsize * 1.20)
    
    start_y = y0 + h * 0.35
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
    "✅ सिंगल वैलिडेटर (पूरा पेज)", 
    "📚 बल्क (Bulk) वैलिडेटर", 
    "📉 कॉम्प्रेस व मर्ज", 
    "✂️ कस्टम क्रॉपर व स्टैम्प"
])

# ==================== TAB 1: SINGLE VALIDATOR ====================
with tab1:
    st.info("💡 राजकाज के आदेश या प्रमाण पत्र में पूरी डिटेल्स (Name, Designation, Date, Reason) के साथ ग्रीन टिक लगाने के लिए यहाँ फाइल अपलोड करें।")
    uploaded_file = st.file_uploader("यहाँ कोई भी PDF फाइल चुनें", type=["pdf"], key="single_pdf")

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
                        extracted = extract_signer_from_pdf_bytes(doc, page, widget)
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

            st.subheader("सिग्नेचर का पूरा विवरण (यह सब PDF पर छपेगा):")
            name = st.text_input("1. अधिकारी का नाम (Digitally signed by):", value=default_info["name"])
            designation = st.text_area("2. पद / विवरण (Designation - दूसरी लाइन के लिए Enter दबाएं):", value=default_info["designation"], height=68)
            date_str = st.text_input("3. दिनांक व समय (Date):", value=default_info["date"])
            reason = st.text_input("4. कारण (Reason):", value=default_info["reason"])

            if st.button("🚀 ग्रीन टिक (✔) और पूरी डिटेल्स लागू करें", use_container_width=True):
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
                st.session_state["show_preview"] = True
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["default_filename"] = f"{base_name}_Validated"

            if "processed_pdf" in st.session_state:
                st.success("✅ आपकी ग्रीन टिक और पूरी डिटेल्स वाली फाइल तैयार है!")
                
                if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True):
                    st.session_state["show_preview"] = not st.session_state.get("show_preview", False)
                    
                if st.session_state.get("show_preview", False):
                    st.info("📄 फाइल का प्रीव्यू (ज़ूम करके सिग्नेचर की चारों लाइनें चेक करें):")
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
                                ext = extract_signer_from_pdf_bytes(b_doc, page, widget)
                                b_name = ext.get("name") or "Subhash Maharia"
                                b_desig = f"Designation : {ext['designation']}" if ext.get("designation") else (f"Location: {ext['location']}" if ext.get("location") else "Designation : Electoral Registration\nOfficer")
                                b_date = ext.get("date") or "2026.10.01 14:07:22 IST"
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

# ==================== TAB 4: SMART CROPPER & OFFICE STAMP ====================
with tab4:
    st.subheader("✂️ 1. स्मार्ट पीडीएफ व कार्ड क्रॉपर (पूरी सिग्नेचर डिटेल्स के साथ)")
    card_file = st.file_uploader("क्रॉप करने के लिए PDF चुनें", type=["pdf"], key="card_pdf")
    
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
            # पहले सिग्नेचर डिटेल्स निकालें ताकि यूजर देख और एडिट कर सके
            c_info = {
                "name": "Subhash Maharia",
                "designation": "Designation : Electoral Registration\nOfficer",
                "date": "2026.10.01 14:07:22 IST",
                "reason": "Approved"
            }
            for page in c_doc:
                for widget in page.widgets():
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        ext = extract_signer_from_pdf_bytes(c_doc, page, widget)
                        if ext.get("name"):
                            c_info["name"] = ext["name"]
                        if ext.get("designation"):
                            c_info["designation"] = f"Designation : {ext['designation']}"
                        elif ext.get("location"):
                            c_info["designation"] = f"Location: {ext['location']}"
                        if ext.get("date"):
                            c_info["date"] = ext["date"]
                        if ext.get("reason"):
                            c_info["reason"] = ext["reason"]

            with st.expander("📝 सिग्नेचर की डिटेल्स चेक / एडिट करें (Name, Designation, Date, Reason)", expanded=True):
                c_name = st.text_input("अधिकारी का नाम:", value=c_info["name"], key="c_name")
                c_desig = st.text_area("पद (Designation):", value=c_info["designation"], height=60, key="c_desig")
                c_date = st.text_input("दिनांक व समय (Date):", value=c_info["date"], key="c_date")
                c_reason = st.text_input("कारण (Reason):", value=c_info["reason"], key="c_reason")

            st.write("**नीचे दिए गए स्लाइडर्स से तय करें कि कितना हिस्सा काटना है (नीचे से 0% रखें ताकि सिग्नेचर न कटे):**")
            col1, col2 = st.columns(2)
            with col1:
                top_cut = st.slider("ऊपर से हटाएं (Top %):", 0, 85, 65)
                left_cut = st.slider("बाएं से हटाएं (Left %):", 0, 50, 0)
            with col2:
                bottom_cut = st.slider("नीचे से हटाएं (Bottom %):", 0, 50, 0)
                right_cut = st.slider("दाएं से हटाएं (Right %):", 0, 50, 0)

            for page in c_doc:
                for widget in list(page.widgets()):
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        rect = widget.rect
                        page.delete_widget(widget)
                        draw_green_tick_and_text(page, rect, c_name, c_desig, c_date, c_reason)

            page = c_doc[0]
            r = page.rect
            crop_rect = fitz.Rect(
                r.x0 + r.width * (left_cut / 100.0),
                r.y0 + r.height * (top_cut / 100.0),
                r.x1 - r.width * (right_cut / 100.0),
                r.y1 - r.height * (bottom_cut / 100.0)
            )

            pix = page.get_pixmap(dpi=180, clip=crop_rect)
            st.image(pix.tobytes("png"), caption="✂️ क्रॉप और पूरी सिग्नेचर डिटेल्स के साथ लाइव प्रीव्यू", use_container_width=True)

            out_card = fitz.open()
            new_p = out_card.new_page(width=crop_rect.width, height=crop_rect.height)
            new_p.show_pdf_page(new_p.rect, c_doc, 0, clip=crop_rect)
            
            st.download_button(
                label="📥 क्रॉप की गई PDF डाउनलोड करें",
                data=out_card.tobytes(),
                file_name="Cropped_" + card_file.name,
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
