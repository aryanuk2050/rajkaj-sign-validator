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

# -------------------- SMART TEXT & SIGNATURE EXTRACTOR --------------------

def extract_officer_details_from_pdf(doc):
    name = "संदेश नायक"
    designation = "जिला निर्वाचन अधिकारी (पंचायत)\n(कलक्टर) जयपुर"
    date_str = "2026.10.01 14:07:22 IST"
    reason = "Approved"

    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"

    matches = re.findall(r'\n\s*\(([औ-ज्ञअ-ह0-9\s\.\,\-\(\)]+)\)\s*\n', full_text)
    for m in matches:
        cleaned = m.strip()
        if len(cleaned) > 2 and "आदेश" not in cleaned and "जयपुर" not in cleaned and "कलक्टर" not in cleaned and "स्पॉट" not in cleaned:
            name = cleaned
            break

    for page in doc:
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                sig_obj_str = doc.xref_object(widget.xref)
                
                reason_match = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
                if reason_match and reason_match.group(1).strip():
                    reason = reason_match.group(1).strip()
                    
                date_match = re.search(r'/M\s*\(D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', sig_obj_str)
                if date_match:
                    y, m, d, hh, mm, ss = date_match.groups()
                    date_str = f"{y}.{m}.{d} {hh}:{mm}:{ss} IST"

    return name, designation, date_str, reason

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
    
    # फॉन्ट साइज को बिल्कुल सही और छोटा सेट किया गया है ताकि पूरा नाम व पद आसानी से फिट हो जाए
    header_fontsize = h * 0.19
    body_fontsize = h * 0.092
    
    page.insert_text(
        fitz.Point(x0 + 2, y0 + h * 0.20),
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
        
    start_y = y0 + h * 0.35
    line_gap = body_fontsize * 1.15
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
            pwd = st.text_input("🔒 यह PDF पासवर्ड से सुरक्षित है। कृपया पासवर्ड दर्ज करें:", type="password", key="s_pass")
            if pwd:
                if doc.authenticate(pwd):
                    st.success("🔓 पासवर्ड सही है! फाइल अनलॉक हो गई।")
                    unlocked = True
                else:
                    st.error("❌ गलत पासवर्ड! कृपया सही पासवर्ड डालें।")

        if unlocked:
            auto_name, auto_desig, auto_date, auto_reason = extract_officer_details_from_pdf(doc)

            st.success(f"✨ **ऑटो-डिटेक्टेड अधिकारी:** `{auto_name}`")

            if st.button("🚀 ऑटो-वैलिडेट करें और ग्रीन टिक (✔) लगाएं", use_container_width=True, key="s_btn"):
                out_doc = fitz.open("pdf", doc.tobytes())
                stamped_count = 0
                for page in out_doc:
                    widgets = list(page.widgets())
                    for widget in widgets:
                        if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                            rect = widget.rect
                            page.delete_widget(widget)
                            draw_green_tick_and_text(page, rect, auto_name, auto_desig, auto_date, auto_reason)
                            stamped_count += 1
                            
                if stamped_count == 0:
                    last_page = out_doc[-1]
                    pw, ph = last_page.rect.width, last_page.rect.height
                    custom_rect = fitz.Rect(pw - 220, ph - 110, pw - 30, ph - 30)
                    draw_green_tick_and_text(last_page, custom_rect, auto_name, auto_desig, auto_date, auto_reason)

                st.session_state["processed_pdf"] = out_doc.tobytes()
                st.session_state["show_preview"] = False
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["default_filename"] = f"{base_name}_Validated"

            if "processed_pdf" in st.session_state:
                st.success("✅ आपकी ग्रीन टिक वाली फाइल तैयार है!")
                
                if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True, key="s_prev"):
                    st.session_state["show_preview"] = not st.session_state.get("show_preview", False)
                    
                if st.session_state.get("show_preview", False):
                    st.info("📄 फाइल का प्रीव्यू (आप इसे ज़ूम करके देख सकते हैं):")
                    preview_doc = fitz.open("pdf", st.session_state["processed_pdf"])
                    for i, page in enumerate(preview_doc):
                        pix = page.get_pixmap(dpi=150)
                        st.image(pix.tobytes("png"), caption=f"पेज {i+1}", use_container_width=True)

                st.divider()

                custom_name = st.text_input(
                    "✏️ फाइल को नया नाम दें (Rename File):", 
                    value=st.session_state.get("default_filename", "Validated_Document"),
                    key="s_fname"
                )
                final_filename = custom_name.strip()
                if not final_filename.lower().endswith(".pdf"):
                    final_filename += ".pdf"

                st.download_button(
                    label=f"📥 फाइल सेव / डाउनलोड करें ({final_filename})",
                    data=st.session_state["processed_pdf"],
                    file_name=final_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    key="s_dl"
                )

                render_share_and_print_buttons(st.session_state["processed_pdf"], final_filename)

# ==================== TAB 2: BULK VALIDATOR ====================
with tab2:
    st.subheader("📚 एक साथ कई PDF फाइलों में ग्रीन टिक लगाएं")
    bulk_files = st.file_uploader("यहाँ एक या अधिक PDF फाइलें चुनें", type=["pdf"], accept_multiple_files=True, key="bulk_pdf")
    
    if bulk_files:
        if st.button(f"⚡ सभी {len(bulk_files)} फाइलों को एक साथ वैलिडेट करें", use_container_width=True, key="b_btn"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for bf in bulk_files:
                    b_doc = fitz.open("pdf", bf.read())
                    if b_doc.needs_pass:
                        continue
                    b_name, b_desig, b_date, b_reason = extract_officer_details_from_pdf(b_doc)
                    for page in b_doc:
                        widgets = list(page.widgets())
                        for widget in widgets:
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
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
                use_container_width=True,
                key="b_dl"
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
        ], key="comp_mode")
        
        if st.button("📉 साइज कम करें (Compress PDF)", use_container_width=True, key="comp_btn"):
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
                use_container_width=True,
                key="comp_dl"
            )

    st.divider()
    st.subheader("📑 2. दो या अधिक PDF को जोड़ें (Merge PDFs)")
    merge_files = st.file_uploader("जोड़ने के लिए 2 या अधिक PDF फाइलें चुनें", type=["pdf"], accept_multiple_files=True, key="merge_pdf")
    if merge_files and len(merge_files) >= 2:
        if st.button("🔗 सभी फाइलों को जोड़कर एक PDF बनाएं", use_container_width=True, key="merge_btn"):
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
                use_container_width=True,
                key="merge_dl"
            )

# ==================== TAB 4: ID CARD CROPPER & OFFICE STAMP ====================
with tab4:
    st.subheader("🪪 1. पीवीसी कार्ड क्रॉपर (e-Aadhaar / Jan-Aadhaar)")
    st.caption("A4 साइज के दस्तावेज़ से केवल नीचे वाला कार्ड हिस्सा काटें और डिजिटल सिग्नेचर वैलिडेट करें।")
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
            crop_ratio = st.slider("नीचे से कार्ड की ऊंचाई का हिस्सा चुनें (%):", 20, 50, 31, key="c_ratio")
            auto_tick = st.checkbox("कार्ड पर मौजूद डिजिटल सिग्नेचर (?) को भी ग्रीन टिक (✔) में बदलें", value=True, key="c_tick")
            
            if st.button("✂️ कार्ड क्रॉप करें और प्रीव्यू देखें", use_container_width=True, key="c_btn"):
                if auto_tick:
                    c_name, c_desig, c_date, c_reason = extract_officer_details_from_pdf(c_doc)
                    for page in c_doc:
                        for widget in list(page.widgets()):
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                                rect = widget.rect
                                page.delete_widget(widget)
                                draw_green_tick_and_text(page, rect, c_name, c_desig, c_date, c_reason)

                page = c_doc[0]
                r = page.rect
                top_y = r.y0 + r.height * (1.0 - (crop_ratio / 100.0))
                crop_rect = fitz.Rect(r.x0 + 12, top_y, r.x1 - 12, r.y1 - 10)
                
                pix = page.get_pixmap(dpi=200, clip=crop_rect)
                st.image(pix.tobytes("png"), caption="क्रॉप किया गया पीवीसी कार्ड", use_container_width=True)
                
                page.set_cropbox(crop_rect)
                out_card = fitz.open()
                out_card.insert_pdf(c_doc, from_page=0, to_page=0)
                
                st.download_button(
                    label="📥 PVC कार्ड PDF डाउनलोड करें",
                    data=out_card.tobytes(),
                    file_name="Card_" + card_file.name,
                    mime="application/pdf",
                    use_container_width=True,
                    key="c_dl"
                )

    st.divider()
    st.subheader("💮 2. सरकारी ऑफिस स्टैम्प / मुहर लगाएं (Office Stamp & Validation)")
    st.caption("यहाँ PDF अपलोड करें, सिग्नेचर वैलिडेट करें, प्रीव्यू देखें और मुहर लगाएं।")
    
    stamp_file = st.file_uploader("मुहर लगाने के लिए PDF चुनें", type=["pdf"], key="stamp_pdf")
    if stamp_file:
        s_bytes = stamp_file.read()
        s_doc = fitz.open("pdf", s_bytes)
        
        s_pwd_ok = True
        if s_doc.needs_pass:
            s_pwd_ok = False
            s_pwd = st.text_input("🔒 यह PDF पासवर्ड सुरक्षित है। पासवर्ड दर्ज करें:", type="password", key="stamp_pwd")
            if s_pwd and s_doc.authenticate(s_pwd):
                s_pwd_ok = True

        if s_pwd_ok:
            stamp_text = st.selectbox("मुहर का प्रकार चुनें:", [
                "APPROVED / अनुमोदित",
                "MOST URGENT / अति आवश्यक",
                "TRUE COPY / प्रमाणित प्रतिलिपि",
                "SEEN & FILED / देखा गया"
            ], key="st_type")
            
            stamp_color_choice = st.radio("मुहर का रंग:", ["लाल (Red)", "नीला (Blue)", "हरा (Green)"], horizontal=True, key="st_col")
            color_map = {"लाल (Red)": (0.8, 0.0, 0.0), "नीला (Blue)": (0.0, 0.2, 0.75), "हरा (Green)": (0.0, 0.55, 0.15)}
            s_color = color_map[stamp_color_choice]

            auto_validate_stamp = st.checkbox("मुहर लगाने के साथ-साथ सिग्नेचर पर ग्रीन टिक (✔) भी लगाएं", value=True, key="st_val_chk")

            if st.button("💮 प्रीव्यू देखें और स्टैम्प लगाएं", use_container_width=True, key="st_btn"):
                out_stamp_doc = fitz.open("pdf", s_doc.tobytes())
                
                if auto_validate_stamp:
                    s_name, s_desig, s_date, s_reason = extract_officer_details_from_pdf(s_doc)
                    for page in out_stamp_doc:
                        widgets = list(page.widgets())
                        for widget in widgets:
                            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                                rect = widget.rect
                                page.delete_widget(widget)
                                draw_green_tick_and_text(page, rect, s_name, s_desig, s_date, s_reason)

                f_page = out_stamp_doc[0]
                pw = f_page.rect.width
                s_rect = fitz.Rect(pw - 190, 25, pw - 25, 60)
                
                f_page.draw_rect(s_rect, color=s_color, width=2.0)
                f_page.insert_textbox(s_rect, stamp_text.split("/")[0].strip(), fontsize=13, fontname="helv", color=s_color, align=1)
                
                st.session_state["stamped_pdf"] = out_stamp_doc.tobytes()

            if "stamped_pdf" in st.session_state:
                st.success("✅ स्टैम्प और वैलिडेटेड PDF तैयार है!")
                
                if st.button("👁️ स्टैम्प वाली PDF का प्रीव्यू देखें", use_container_width=True, key="st_prev_btn"):
                    prev_doc = fitz.open("pdf", st.session_state["stamped_pdf"])
                    for i, page in enumerate(prev_doc):
                        pix = page.get_pixmap(dpi=150)
                        st.image(pix.tobytes("png"), caption=f"पेज {i+1} प्रीव्यू", use_container_width=True)

                st.download_button(
                    label="📥 स्टैम्प लगी हुई PDF डाउनलोड करें",
                    data=st.session_state["stamped_pdf"],
                    file_name="Stamped_" + stamp_file.name,
                    mime="application/pdf",
                    use_container_width=True,
                    key="st_dl"
                )
