import streamlit as st
import fitz  # PyMuPDF
import re
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="RajKaj DSC Validator", page_icon="✅")
st.title("✅ राजकाज डिजिटल सिग्नेचर वैलिडेटर")
st.write("अपनी PDF फाइल अपलोड करें और क्वेश्चन मार्क (?) को हूबहू Adobe जैसे ग्रीन टिक (✔) में बदलें।")

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

def draw_green_tick_and_text(page, rect, name, designation, date_str, reason, x_shift=0.0, slim_factor=1.0):
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    
    w, h = rect.width, rect.height
    x0, y0 = rect.x0, rect.y0

    t_left = 0.032 * slim_factor
    t_right = 0.039 * slim_factor

    # ओरिजिनल इमेज के अनुसार 'v' और 'd' पर सटीक बैठने वाले कोऑर्डिनेट्स
    sx = x_shift * w
    pts_main = [
        fitz.Point(x0 + w * 0.310 + sx, y0 + h * 0.585),                 # p0: बायां बाहरी कोना ('.' के ऊपर)
        fitz.Point(x0 + w * (0.310 + t_left) + sx, y0 + h * 0.505),      # p1: बायां ऊपरी कोना ('E' के पास)
        fitz.Point(x0 + w * 0.435 + sx, y0 + h * 0.720),                 # p2: बीच का V-मोड़ ('01' के बीच)
        fitz.Point(x0 + w * 0.595 + sx, y0 + h * 0.190),                 # p3: दायां ऊपरी कोना ('valid' के 'v' पर)
        fitz.Point(x0 + w * (0.595 + t_right) + sx, y0 + h * 0.260),     # p4: दायां बाहरी कोना ('v' और 'a' के बीच)
        fitz.Point(x0 + w * 0.445 + sx, y0 + h * 0.875),                 # p5: सबसे नीचे की नोक ('Approved' के 'd' पर)
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
    
    # 'Signature valid' का साइज ओरिजिनल के बराबर (0.215)
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

    st.subheader("सिग्नेचर विवरण (आप इसे आवश्यकतानुसार एडिट भी कर सकते हैं):")
    name = st.text_input("अधिकारी का नाम (Digitally signed by):", value=default_info["name"])
    designation = st.text_area("पद (Designation - दूसरी लाइन के लिए Enter दबाएं):", value=default_info["designation"], height=68)
    date_str = st.text_input("दिनांक व समय (Date):", value=default_info["date"])
    reason = st.text_input("कारण (Reason):", value=default_info["reason"])

    with st.expander("⚙️ टिक की पोजिशन और मोटाई एडजस्ट करें (वैकल्पिक)"):
        x_shift = st.slider("बाएं / दाएं खिसकाएं (Left / Right):", -0.20, 0.20, 0.0, 0.01)
        slim_factor = st.slider("टिक की मोटाई (Thickness):", 0.6, 1.5, 1.0, 0.05)

    if st.button("🚀 ग्रीन टिक (✔) लागू करें और PDF बनाएं"):
        out_doc = fitz.open("pdf", pdf_bytes)
        stamped_count = 0
        
        for page in out_doc:
            widgets = list(page.widgets())
            for widget in widgets:
                if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                    rect = widget.rect
                    page.delete_widget(widget)
                    draw_green_tick_and_text(page, rect, name, designation, date_str, reason, x_shift, slim_factor)
                    stamped_count += 1
                    
        if stamped_count == 0:
            st.warning("इस PDF में ऑटोमैटिक सिग्नेचर बॉक्स नहीं मिला। अंतिम पेज पर दाईं ओर नीचे स्टैम्प लगाया जा रहा है।")
            last_page = out_doc[-1]
            pw, ph = last_page.rect.width, last_page.rect.height
            custom_rect = fitz.Rect(pw - 220, ph - 110, pw - 30, ph - 30)
            draw_green_tick_and_text(last_page, custom_rect, name, designation, date_str, reason, x_shift, slim_factor)

        output_pdf = out_doc.tobytes()
        st.success("✅ आपकी फाइल तैयार है! नीचे बटन दबाकर डाउनलोड करें।")
        st.download_button(
            label="📥 वैलिडेटेड PDF डाउनलोड करें",
            data=output_pdf,
            file_name="Validated_" + uploaded_file.name,
            mime="application/pdf"
        )
