import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
import re
import base64
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="RajKaj DSC Validator", page_icon="✅")
st.title("✅ राजकाज डिजिटल सिग्नेचर वैलिडेटर")
st.write("अपनी PDF फाइल अपलोड करें और क्वेश्चन मार्क (?) को ग्रीन टिक (✔) में बदलें।")

def extract_signer_from_pdf_bytes(pdf_bytes, xref):
    info = {"name": "", "designation": "", "date": "", "reason": "Approved"}
    try:
        doc = fitz.open("pdf", pdf_bytes)
        sig_obj_str = doc.xref_object(xref)
        
        reason_match = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
        if reason_match and reason_match.group(1).strip():
            info["reason"] = reason_match.group(1).strip()
            
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
                    elif attr.oid in (x509.NameOID.TITLE, x509.NameOID.ORGANIZATIONAL_UNIT_NAME):
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

    # एकदम सटीक फिक्स कोऑर्डिनेट्स
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
        for idx, d_line in enumerate(designation.splitlines()):
            if idx == 0:
                raw_lines.append(f"Designation : {d_line}")
            else:
                raw_lines.append(d_line)
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

uploaded_file = st.file_uploader("यहाँ राजकाज की PDF फाइल चुनें", type=["pdf"])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    default_info = {
        "name": "Subhash Maharia", 
        "designation": "Electoral Registration\nOfficer", 
        "date": "2026.10.01 14:07:22 IST", 
        "reason": "Approved"
    }
    
    for page in doc:
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                extracted = extract_signer_from_pdf_bytes(pdf_bytes, widget.xref)
                for k in default_info:
                    if extracted.get(k):
                        default_info[k] = extracted[k]

    st.subheader("सिग्नेचर विवरण:")
    name = st.text_input("अधिकारी का नाम (Digitally signed by):", value=default_info["name"])
    designation = st.text_area("पद (Designation - दूसरी लाइन के लिए Enter दबाएं):", value=default_info["designation"], height=68)
    date_str = st.text_input("दिनांक व समय (Date):", value=default_info["date"])
    reason = st.text_input("कारण (Reason):", value=default_info["reason"])

    if st.button("🚀 ग्रीन टिक (✔) लागू करें और PDF तैयार करें", use_container_width=True):
        out_doc = fitz.open("pdf", pdf_bytes)
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

    # जब PDF प्रोसेस हो जाए, तब View, Rename, Download और Share के विकल्प दिखाएं
    if "processed_pdf" in st.session_state:
        st.success("✅ आपकी ग्रीन टिक वाली फाइल तैयार है!")
        
        # 1. VIEW (प्रीव्यू देखने का बटन)
        if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True):
            st.session_state["show_preview"] = not st.session_state.get("show_preview", False)
            
        if st.session_state.get("show_preview", False):
            st.info("📄 फाइल का प्रीव्यू (आप इसे ज़ूम करके देख सकते हैं):")
            preview_doc = fitz.open("pdf", st.session_state["processed_pdf"])
            for i, page in enumerate(preview_doc):
                pix = page.get_pixmap(dpi=150)
                st.image(pix.tobytes("png"), caption=f"पेज {i+1}", use_container_width=True)

        st.divider()

        # 2. RENAME (फाइल का नाम बदलने का ऑप्शन)
        custom_name = st.text_input(
            "✏️ फाइल को नया नाम दें (Rename File):", 
            value=st.session_state.get("default_filename", "Validated_Document")
        )
        final_filename = custom_name.strip()
        if not final_filename.lower().endswith(".pdf"):
            final_filename += ".pdf"

        # 3. DOWNLOAD / SAVE (फोन में सेव करने का बटन)
        st.download_button(
            label=f"📥 फाइल सेव / डाउनलोड करें ({final_filename})",
            data=st.session_state["processed_pdf"],
            file_name=final_filename,
            mime="application/pdf",
            use_container_width=True
        )

        # 4. SHARE (सीधे WhatsApp, Telegram, Email आदि पर भेजने का बटन)
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
                        text: "वैलिडेटेड राजकाज दस्तावेज़"
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
