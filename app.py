import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
import re
import base64
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="Universal DSC Validator", page_icon="✅")
st.title("✅ डिजिटल सिग्नेचर वैलिडेटर (All-in-One)")
st.write("राजकाज, ई-आधार, जाति/मूल निवास व अन्य सभी प्रमाण पत्रों के क्वेश्चन मार्क (?) को ग्रीन टिक (✔) में बदलें।")

def extract_signer_from_pdf_bytes(doc, xref):
    info = {"name": "", "designation": "", "location": "", "date": "", "reason": ""}
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
                subject = certs[0].subject
                for attr in subject:
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

uploaded_file = st.file_uploader("यहाँ कोई भी PDF फाइल चुनें (राजकाज / ई-आधार / प्रमाण पत्र)", type=["pdf"])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    # यदि फाइल में पासवर्ड लगा हो (जैसे e-Aadhaar)
    unlocked = True
    if doc.needs_pass:
        unlocked = False
        pwd = st.text_input("🔒 यह PDF पासवर्ड से सुरक्षित है (जैसे e-Aadhaar)। कृपया पासवर्ड दर्ज करें:", type="password")
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
            "reason": "Approved"
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

        st.subheader("सिग्नेचर विवरण:")
        name = st.text_input("हस्ताक्षरकर्ता / विभाग (Digitally signed by):", value=default_info["name"])
        designation = st.text_area("पद / विवरण (दूसरी लाइन के लिए Enter दबाएं):", value=default_info["designation"], height=68)
        date_str = st.text_input("दिनांक व समय (Date):", value=default_info["date"])
        reason = st.text_input("कारण (Reason - यदि खाली रखना हो तो मिटा दें):", value=default_info["reason"])

        if st.button("🚀 ग्रीन टिक (✔) लागू करें और PDF तैयार करें", use_container_width=True):
            for page in doc:
                widgets = list(page.widgets())
                stamped_count = 0
                for widget in widgets:
                    if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                        rect = widget.rect
                        page.delete_widget(widget)
                        draw_green_tick_and_text(page, rect, name, designation, date_str, reason)
                        stamped_count += 1
                        
            st.session_state["processed_pdf"] = doc.tobytes()
            st.session_state["show_preview"] = False
            base_name = uploaded_file.name.rsplit(".", 1)[0]
            st.session_state["default_filename"] = f"{base_name}_Validated"

        if "processed_pdf" in st.session_state:
            st.success("✅ आपकी ग्रीन टिक वाली फाइल तैयार है!")
            
            if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True):
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

            b64_pdf = base64.b64encode(st.session_state["processed_pdf"]).decode("utf-8")
            share_html = f"""
            <button onclick="sharePDF()" style="
                width: 100%;
                padding: 12px;
                background-color: #25D366;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                cursor: pointer;
                margin-top: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.15);">
                📤 कहीं भी शेयर करें (WhatsApp / Telegram / Mail)
            </button>
            <script>
            async function sharePDF() {{
                const b64Data = "{b64_pdf}";
                const byteCharacters = atob(b64Data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {{
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNumbers);
                const file = new File([byteArray], "{final_filename}", {{ type: "application/pdf" }});

                if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                    try {{
                        await navigator.share({{
                            files: [file],
                            title: "{final_filename}",
                            text: "वैलिडेटेड दस्तावेज़"
                        }});
                    }} catch (err) {{
                        console.log("Share cancelled", err);
                    }}
                }} else {{
                    alert("आपके ब्राउज़र में डायरेक्ट शेयर सपोर्ट नहीं है, कृपया ऊपर दिए गए डाउनलोड बटन से सेव करके शेयर करें।");
                }}
            }}
            </script>
            """
            components.html(share_html, height=65)
