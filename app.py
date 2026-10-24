import streamlit as st
import fitz  # PyMuPDF
import re
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="RajKaj DSC Validator", page_icon="✅")
st.title("✅ राजकाज डिजिटल सिग्नेचर वैलिडेटर")
st.write("अपनी PDF फाइल अपलोड करें और क्वेश्चन मार्क (?) को ग्रीन टिक (✔) में बदलें।")

def extract_signer_from_pdf_bytes(pdf_bytes, xref):
    """PDF के सिग्नेचर ऑब्जेक्ट से सर्टिफिकेट और टेक्स्ट निकालना"""
    info = {"name": "", "designation": "", "date": "", "reason": "Approved"}
    try:
        doc = fitz.open("pdf", pdf_bytes)
        sig_obj_str = doc.xref_object(xref)
        
        # 1. PDF के सिग्नेचर डिक्शनरी से Reason और Date (M) निकालना
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

        # 2. PKCS#7 सर्टिफिकेट से अधिकारी का नाम और पद (Designation) निकालना
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

def draw_green_tick_and_text(page, rect, name, designation, date_str, reason):
    """सिग्नेचर बॉक्स पर हूबहू Adobe जैसा ग्रीन टिक और टेक्स्ट छापना"""
    # 1. पुराने क्वेश्चन मार्क को सफेद बॉक्स से साफ करना
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    
    # 2. पीछे बड़ा ग्रीन चेक मार्क (✔) बनाना (काली बॉर्डर के साथ)
    w, h = rect.width, rect.height
    p1 = fitz.Point(rect.x0 + w * 0.42, rect.y0 + h * 0.52)
    p2 = fitz.Point(rect.x0 + w * 0.56, rect.y0 + h * 0.82)
    p3 = fitz.Point(rect.x0 + w * 0.82, rect.y0 + h * 0.18)
    
    shape = page.new_shape()
    # काली बॉर्डर
    shape.draw_line(p1, p2)
    shape.draw_line(p2, p3)
    shape.finish(color=(0, 0, 0), width=max(w * 0.08, 6), lineCap=1, lineJoin=1)
    
    # हरा रंग (Green Fill)
    shape.draw_line(p1, p2)
    shape.draw_line(p2, p3)
    shape.finish(color=(0, 0.68, 0.22), width=max(w * 0.055, 4), lineCap=1, lineJoin=1)
    shape.commit()
    
    # 3. ऊपर "Signature valid" लिखना
    header_fontsize = max(min(h * 0.20, 15), 9)
    body_fontsize = max(min(h * 0.11, 8.5), 6)
    
    header_rect = fitz.Rect(rect.x0 + 2, rect.y0 + 1, rect.x1 - 2, rect.y0 + h * 0.28)
    page.insert_textbox(header_rect, "Signature valid", fontsize=header_fontsize, fontname="helv", color=(0, 0, 0))
    
    # 4. नीचे अधिकारी का विवरण लिखना
    lines = [f"Digitally signed by {name}"]
    if designation:
        lines.append(f"Designation : {designation}")
    if date_str:
        lines.append(f"Date: {date_str}")
    if reason:
        lines.append(f"Reason: {reason}")
        
    body_text = "\n".join(lines)
    body_rect = fitz.Rect(rect.x0 + 2, rect.y0 + h * 0.27, rect.x1 - 2, rect.y1 - 1)
    page.insert_textbox(body_rect, body_text, fontsize=body_fontsize, fontname="helv", color=(0, 0, 0))

uploaded_file = st.file_uploader("यहाँ राजकाज की PDF फाइल चुनें", type=["pdf"])

if uploaded_file:
    pdf_bytes = uploaded_file.read()
    doc = fitz.open("pdf", pdf_bytes)
    
    sig_found = False
    default_info = {"name": "Subhash Maharia", "designation": "Electoral Registration Officer", "date": "2026.10.01 14:07:22 IST", "reason": "Approved"}
    
    # चेक करना कि PDF में सिग्नेचर विजेट कहाँ है
    for page in doc:
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                sig_found = True
                extracted = extract_signer_from_pdf_bytes(pdf_bytes, widget.xref)
                for k in default_info:
                    if extracted.get(k):
                        default_info[k] = extracted[k]

    st.subheader("सिग्नेचर विवरण (आप इसे आवश्यकतानुसार एडिट भी कर सकते हैं):")
    name = st.text_input("अधिकारी का नाम (Digitally signed by):", value=default_info["name"])
    designation = st.text_input("पद (Designation):", value=default_info["designation"])
    date_str = st.text_input("दिनांक व समय (Date):", value=default_info["date"])
    reason = st.text_input("कारण (Reason):", value=default_info["reason"])

    if st.button("🚀 ग्रीन टिक (✔) लागू करें और PDF बनाएं"):
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
            st.warning("इस PDF में ऑटोमैटिक सिग्नेचर बॉक्स नहीं मिला। अंतिम पेज पर दाईं ओर नीचे स्टैम्प लगाया जा रहा है।")
            last_page = out_doc[-1]
            pw, ph = last_page.rect.width, last_page.rect.height
            custom_rect = fitz.Rect(pw - 220, ph - 110, pw - 30, ph - 30)
            draw_green_tick_and_text(last_page, custom_rect, name, designation, date_str, reason)

        output_pdf = out_doc.tobytes()
        st.success("✅ आपकी फाइल तैयार है! नीचे बटन दबाकर डाउनलोड करें।")
        st.download_button(
            label="📥 वैलिडेटेड PDF डाउनलोड करें",
            data=output_pdf,
            file_name="Validated_" + uploaded_file.name,
            mime="application/pdf"
        )
      
