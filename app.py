import streamlit as st
import streamlit.components.v1 as components
import fitz  # PyMuPDF
import re
import io
import zipfile
import base64
from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7

st.set_page_config(page_title="Universal DSC Validator & Toolkit", page_icon="✅", layout="centered")
st.title("✅ यूनिवर्सल डिजिटल सिग्नेचर वैलिडेटर एवं पीडीएफ टूलकिट")
st.caption("राजकाज, ई-आधार, ई-मित्र व सभी विभागीय आदेशों के लिए 100% ऑटोमैटिक पीडीएफ सॉल्यूशन (मल्टी-पेज सपोर्ट)")

# -------------------- CLEAN ENGLISH & TEXT FORMATTER --------------------

ADMIN_VOCAB = {
    "कार्यालय": "Office of",
    "जिला निर्वाचन अधिकारी": "District Election Officer",
    "निर्वाचक रजिस्ट्रीकरण पदाधिकारी": "Electoral Registration Officer",
    "उप जिला निर्वाचन अधिकारी": "Deputy District Election Officer",
    "अतिरिक्त जिला कलक्टर": "Additional District Collector",
    "अतिरिक्त जिला कलेक्टर": "Additional District Collector",
    "जिला कलक्टर एवं जिला मजिस्ट्रेट": "Collector & District Magistrate",
    "जिला कलक्टर": "District Collector",
    "जिला कलेक्टर": "District Collector",
    "कलक्टर": "Collector",
    "कलेक्टर": "Collector",
    "उपखण्ड अधिकारी": "Sub Divisional Officer",
    "उपखंड अधिकारी": "Sub Divisional Officer",
    "तहसीलदार": "Tehsildar",
    "नायब तहसीलदार": "Naib Tehsildar",
    "विकास अधिकारी": "Block Development Officer",
    "मुख्य कार्यकारी अधिकारी": "Chief Executive Officer",
    "शासन सचिव": "Secretary to Government",
    "संयुक्त शासन सचिव": "Joint Secretary",
    "उप शासन सचिव": "Deputy Secretary",
    "निदेशक": "Director",
    "अतिरिक्त निदेशक": "Additional Director",
    "संयुक्त निदेशक": "Joint Director",
    "उप निदेशक": "Deputy Director",
    "सहायक निदेशक": "Assistant Director",
    "मुख्य अभियंता": "Chief Engineer",
    "अधीक्षण अभियंता": "Superintending Engineer",
    "अधिशाषी अभियंता": "Executive Engineer",
    "सहायक अभियंता": "Assistant Engineer",
    "मुख्य जिला शिक्षा अधिकारी": "Chief District Education Officer",
    "जिला शिक्षा अधिकारी": "District Education Officer",
    "प्रधानाचार्य": "Principal",
    "मुख्य चिकित्सा एवं स्वास्थ्य अधिकारी": "Chief Medical & Health Officer",
    "पुलिस अधीक्षक": "Superintendent of Police",
    "कोषाधिकारी": "Treasury Officer",
    "लेखाधिकारी": "Accounts Officer",
    "आयुक्त": "Commissioner",
    "उपायुक्त": "Deputy Commissioner",
    "तहसील": "Tehsil",
    "पंचायत": "Panchayat",
    "राजस्थान": "Rajasthan",
    "जयपुर": "Jaipur", "जोधपुर": "Jodhpur", "उदयपुर": "Udaipur", "अजमेर": "Ajmer",
    "कोटा": "Kota", "बीकानेर": "Bikaner", "भरतपुर": "Bharatpur", "सीकर": "Sikar",
    "अलवर": "Alwar", "भीलवाड़ा": "Bhilwara", "पाली": "Pali", "चूरू": "Churu",
    "झुंझुनूं": "Jhunjhunu", "नागौर": "Nagaur", "गंगानगर": "Sri Ganganagar",
    "हनुमानगढ़": "Hanumangarh", "बाड़मेर": "Barmer", "जैसलमेर": "Jaisalmer",
    "जालोर": "Jalore", "सिरोही": "Sirohi", "डूंगरपुर": "Dungarpur", "बांसवाड़ा": "Banswara",
    "चित्तौड़गढ़": "Chittorgarh", "राजसमंद": "Rajsamand", "प्रतापगढ़": "Pratapgarh",
    "बूंदी": "Bundi", "बारां": "Baran", "झालावाड़": "Jhalawar", "सवाई माधोपुर": "Sawai Madhopur",
    "करौली": "Karauli", "धौलपुर": "Dholpur", "दौसा": "Dausa", "टोंक": "Tonk",
}

def to_clean_english(text):
    if not text:
        return ""
    text = text.strip()
    if all(ord(c) < 128 for c in text):
        return text

    res = text
    for hi, en in sorted(ADMIN_VOCAB.items(), key=lambda x: len(x[0]), reverse=True):
        res = res.replace(hi, f" {en} ")

    consonants = {
        'क': 'k', 'ख': 'kh', 'ग': 'g', 'घ': 'gh', 'ङ': 'n',
        'च': 'ch', 'छ': 'chh', 'ज': 'j', 'झ': 'jh', 'ञ': 'n',
        'ट': 't', 'ठ': 'th', 'ड': 'd', 'ढ': 'dh', 'ण': 'n',
        'त': 't', 'थ': 'th', 'द': 'd', 'ध': 'dh', 'न': 'n',
        'प': 'p', 'फ': 'ph', 'ब': 'b', 'भ': 'bh', 'म': 'm',
        'य': 'y', 'र': 'r', 'ल': 'l', 'व': 'v', 'श': 'sh',
        'ष': 'sh', 'स': 's', 'ह': 'h', 'क्ष': 'ksh', 'त्र': 'tr', 'ज्ञ': 'gy',
        'ड़': 'd', 'ढ़': 'dh', 'क़': 'q', 'ख़': 'kh', 'ग़': 'gh', 'ज़': 'z', 'फ़': 'f'
    }
    vowels = {
        'अ': 'a', 'आ': 'aa', 'इ': 'i', 'ई': 'ee', 'उ': 'u', 'ऊ': 'oo',
        'ऋ': 'ri', 'ए': 'e', 'ऐ': 'ai', 'ओ': 'o', 'औ': 'au'
    }
    matras = {
        'ा': 'a', 'ि': 'i', 'ी': 'ee', 'ु': 'u', 'ू': 'oo',
        'ृ': 'ri', 'े': 'e', 'ै': 'ai', 'ो': 'o', 'ौ': 'au',
        'ं': 'n', 'ँ': 'n', 'ः': 'h', '्': ''
    }

    out = []
    i = 0
    n = len(res)
    while i < n:
        ch = res[i]
        if ord(ch) < 128:
            out.append(ch)
            i += 1
        elif ch in vowels:
            if i + 1 < n and res[i + 1] in ('ं', 'ँ'):
                out.append(vowels[ch] + 'n')
                i += 2
            else:
                out.append(vowels[ch])
                i += 1
        elif ch in consonants:
            base = consonants[ch]
            if i + 1 < n and res[i + 1] == '्':
                out.append(base)
                i += 2
            elif i + 1 < n and res[i + 1] in matras:
                m = res[i + 1]
                if m in ('ं', 'ँ'):
                    out.append(base + 'an')
                    i += 2
                else:
                    vowel_part = matras[m]
                    if i + 2 < n and res[i + 2] in ('ं', 'ँ'):
                        out.append(base + vowel_part + 'n')
                        i += 3
                    else:
                        out.append(base + vowel_part)
                        i += 2
            else:
                next_is_dev = (i + 1 < n) and ('\u0900' <= res[i + 1] <= '\u097F')
                out.append(base if not next_is_dev else base + 'a')
                i += 1
        elif ch in matras:
            out.append(matras[ch])
            i += 1
        else:
            i += 1

    raw_en = "".join(out)
    cleaned_lines = []
    for line in raw_en.splitlines():
        words = [w.capitalize() if w.islower() else w for w in line.split() if w.strip()]
        if words:
            cleaned_lines.append(" ".join(words))
    return "\n".join(cleaned_lines)


# -------------------- EXACT SIGNATURE TEXT & CERT PARSER --------------------

def is_valid_text(val):
    if not val or len(val.strip()) < 2:
        return False
    low = val.lower().strip()
    junk = [
        "itext", "agpl", "version", "adobe", "pkcs7", "subfilter", "adbe",
        "sha256", "signing", "unknown", "null", "none", "signature valid", "signature not verified"
    ]
    return not any(j in low for j in junk)

def is_invalid_designation(val):
    if not val or len(val.strip()) < 2:
        return True
    low = val.lower().strip()
    bad_desigs = [
        "raj esign", "rajesign", "e-sign", "esign", "doit", "doit&c", "ris", "risl",
        "personal", "individual", "class 2", "class 3", "unspecified", "na", "n/a",
        "nic", "emudhra", "cdac", "c-dac", "csc", "protean", "nsdl", "capricorn", "verasys"
    ]
    return low in bad_desigs or any(b == low for b in bad_desigs)

def is_ca_name(val):
    low = val.lower()
    ca_keywords = [
        "certifying authority", "ca 20", "sub ca", "root ca", "emudhra",
        "nic sub-ca", "cdac", "ncode", "capricorn", "sify", "verasys",
        "csc e-governance", "protean", "nsdl", "c-dac", "raj esign"
    ]
    return any(k in low for k in ca_keywords)

def parse_combined_signature_block(raw_text):
    p_name, p_desig, p_date, p_reason = "", "", "", ""
    if not raw_text:
        return p_name, p_desig, p_date, p_reason

    flat = " ".join([ln.strip() for ln in raw_text.splitlines() if ln.strip()])
    flat = re.sub(r'(?i)signature\s+not\s+verified|signature\s+valid|\?', ' ', flat).strip()

    m_name = re.search(
        r'(?i)digitally\s+signed\s+by\s*:?\s*(.+?)(?=\s+designation\s*:|\s+date\s*:|\s+reason\s*:|\s+location\s*:|$)',
        flat
    )
    if m_name:
        cand = m_name.group(1).strip()
        if is_valid_text(cand) and not is_ca_name(cand):
            p_name = cand

    m_desig = re.search(
        r'(?i)designation\s*:\s*(.+?)(?=\s+date\s*:|\s+reason\s*:|\s+location\s*:|$)',
        flat
    )
    if m_desig:
        cand = m_desig.group(1).strip()
        if is_valid_text(cand) and not is_invalid_designation(cand):
            p_desig = cand

    m_date = re.search(
        r'(?i)date\s*:\s*([0-9]{4}[\.\-\/][0-9]{2}[\.\-\/][0-9]{2}\s+[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\s*[A-Za-z\+0-9\:]*)?)',
        flat
    )
    if m_date:
        p_date = m_date.group(1).strip()

    m_reason = re.search(
        r'(?i)reason\s*:\s*(.+?)(?=\s+location\s*:|\s+date\s*:|$)',
        flat
    )
    if m_reason:
        cand = m_reason.group(1).strip()
        if is_valid_text(cand):
            p_reason = cand

    return p_name, p_desig, p_date, p_reason

def wrap_designation_smartly(desig_str):
    if not desig_str:
        return ""
    desig_str = " ".join(desig_str.split())
    if len(desig_str) <= 22:
        return desig_str
    words = desig_str.split(" ")
    line1, line2 = [], []
    curr_len = 0
    for w in words:
        if curr_len + len(w) <= 20 or not line1:
            line1.append(w)
            curr_len += len(w) + 1
        else:
            line2.append(w)
    if line2:
        return " ".join(line1) + "\n" + " ".join(line2)
    return desig_str

def extract_universal_signature_details(doc):
    found_name = ""
    found_desig = ""
    found_date = ""
    found_reason = ""

    for page in doc:
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                try:
                    box_text = page.get_text("text", clip=widget.rect)
                    n1, d1, dt1, r1 = parse_combined_signature_block(box_text)
                    if n1: found_name = n1
                    if d1: found_desig = d1
                    if dt1: found_date = dt1
                    if r1: found_reason = r1
                except Exception:
                    pass

                sig_obj_str = doc.xref_object(widget.xref)
                v_match = re.search(r'/V\s+(\d+)\s+0\s+R', sig_obj_str)
                if v_match:
                    try:
                        sig_obj_str += "\n" + doc.xref_object(int(v_match.group(1)))
                    except Exception:
                        pass

                ap_refs = re.findall(r'(\d+)\s+0\s+R', sig_obj_str)
                stream_texts = []
                for ref_str in ap_refs[:12]:
                    try:
                        s_bytes = doc.xref_stream(int(ref_str))
                        if s_bytes:
                            s_txt = s_bytes.decode('latin1', errors='ignore')
                            for p_match in re.findall(r'\(([^()]{2,200})\)', s_txt):
                                clean_p = p_match.replace('\\(', '(').replace('\\)', ')').strip()
                                stream_texts.append(clean_p)
                    except Exception:
                        pass

                if stream_texts:
                    combined_stream = " ".join(stream_texts)
                    n2, d2, dt2, r2 = parse_combined_signature_block(combined_stream)
                    if n2 and not found_name: found_name = n2
                    if d2 and not found_desig: found_desig = d2
                    if dt2 and not found_date: found_date = dt2
                    if r2 and not found_reason: found_reason = r2

                contents_match = re.search(r'/Contents\s*<([0-9A-Fa-f\s]+)>', sig_obj_str)
                if contents_match:
                    try:
                        hex_data = re.sub(r'\s+', '', contents_match.group(1)).rstrip('0')
                        if len(hex_data) % 2 != 0:
                            hex_data += '0'
                        der_bytes = bytes.fromhex(hex_data)
                        certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
                        for cert in certs:
                            cn, title, ou, org = "", "", "", ""
                            for attr in cert.subject:
                                val = attr.value.strip() if isinstance(attr.value, str) else ""
                                if attr.oid == x509.NameOID.COMMON_NAME: cn = val
                                elif attr.oid == x509.NameOID.TITLE: title = val
                                elif attr.oid == x509.NameOID.ORGANIZATIONAL_UNIT_NAME: ou = val
                                elif attr.oid == x509.NameOID.ORGANIZATION_NAME: org = val

                            if cn and not is_ca_name(cn) and is_valid_text(cn):
                                if "designation" in cn.lower():
                                    cn_n, cn_d, _, _ = parse_combined_signature_block("Digitally signed by " + cn)
                                    if cn_n and not found_name: found_name = cn_n
                                    if cn_d and not found_desig: found_desig = cn_d
                                elif not found_name:
                                    found_name = cn

                                if not found_desig:
                                    if title and not is_invalid_designation(title): found_desig = title
                                    elif ou and not is_invalid_designation(ou): found_desig = ou
                                    elif org and not is_invalid_designation(org) and not is_ca_name(org): found_desig = org
                    except Exception:
                        pass

                if not found_date:
                    d_m = re.search(r'/M\s*\(D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', sig_obj_str)
                    if d_m:
                        y, m, d, hh, mm, ss = d_m.groups()
                        found_date = f"{y}.{m}.{d} {hh}:{mm}:{ss} IST"

                if not found_reason:
                    r_m = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
                    if r_m and is_valid_text(r_m.group(1)):
                        found_reason = r_m.group(1).strip()

                if not found_name:
                    n_m = re.search(r'/Name\s*\((.*?)\)', sig_obj_str)
                    if n_m and is_valid_text(n_m.group(1)) and not is_ca_name(n_m.group(1)):
                        raw_nm = n_m.group(1).strip()
                        if "designation" in raw_nm.lower():
                            nm_only, ds_only, _, _ = parse_combined_signature_block("Digitally signed by " + raw_nm)
                            found_name = nm_only or raw_nm
                            if ds_only and not found_desig: found_desig = ds_only
                        else:
                            found_name = raw_nm

    if "designation" in found_name.lower():
        parts = re.split(r'(?i)\s*designation\s*:\s*', found_name, maxsplit=1)
        found_name = parts[0].strip()
        if len(parts) > 1 and parts[1].strip() and (not found_desig or is_invalid_designation(found_desig)):
            found_desig = parts[1].strip()

    if not found_name or not found_desig or is_invalid_designation(found_desig):
        full_text = ""
        for page in doc:
            full_text += page.get_text("text") + "\n"
        lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
        
        non_person = [
            "कलक्टर", "कलेक्टर", "पंचायत", "आदेश", "जयपुर", "जोधपुर", "उदयपुर", "अजमेर", "कोटा",
            "बीकानेर", "भरतपुर", "राजस्थान", "प्रभारी", "महोदय", "समस्त", "जिला", "कार्यालय",
            "विभाग", "समिति", "परिषद", "निगम", "योजना", "प्रकोष्ठ", "शाखा", "अनुभाग", "पीआरओ"
        ]
        for idx, ln in enumerate(lines):
            m = re.match(r'^\(\s*([औ-ज्ञअ-हA-Za-z\.\s]{3,42})\s*\)$', ln)
            if m:
                cand_name = m.group(1).strip()
                if not any(w in cand_name.lower() for w in non_person):
                    if not found_name: found_name = cand_name
                    if not found_desig or is_invalid_designation(found_desig):
                        d_parts = []
                        for next_i in range(idx + 1, min(idx + 3, len(lines))):
                            nxt_line = lines[next_i]
                            if any(stop in nxt_line for stop in ["क्रमांक", "दिनांक", "प्रतिलिपि", "1.", "2.", "RajKaj", "Signature"]):
                                break
                            d_parts.append(nxt_line)
                        if d_parts:
                            found_desig = " ".join(d_parts)
                    break

    final_name = to_clean_english(found_name) if found_name else "Authorized Signatory"
    final_desig = wrap_designation_smartly(to_clean_english(found_desig)) if (found_desig and not is_invalid_designation(found_desig)) else ""
    final_date = found_date if found_date else ""
    final_reason = to_clean_english(found_reason) if found_reason else "Approved"

    return final_name, final_desig, final_date, final_reason


# -------------------- ADOBE READER STYLE GREEN TICK & TEXT --------------------

def draw_exact_tick_polygon(shape, pts, fill_color, stroke_color=None, stroke_width=1.0):
    shape.draw_quad(fitz.Quad(pts[0], pts[1], pts[5], pts[2]))
    shape.draw_quad(fitz.Quad(pts[2], pts[3], pts[5], pts[4]))
    shape.finish(color=fill_color, fill=fill_color, width=0)

    if stroke_color and stroke_width > 0:
        for i in range(6):
            shape.draw_line(pts[i], pts[(i + 1) % 6])
        shape.finish(color=stroke_color, width=stroke_width, lineCap=0, lineJoin=0)

def draw_green_tick_and_text(page, rect, name, designation, date_str, reason):
    safe_name = to_clean_english(name).strip()
    safe_desig = to_clean_english(designation).strip()
    safe_date = to_clean_english(date_str).strip()
    safe_reason = to_clean_english(reason).strip()

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
    
    raw_lines = [f"Digitally signed by {safe_name}"]
    if safe_desig:
        for idx, d_line in enumerate(safe_desig.splitlines()):
            clean_d = d_line.strip()
            if clean_d:
                if idx == 0 and not clean_d.lower().startswith("designation") and not clean_d.lower().startswith("location"):
                    raw_lines.append(f"Designation : {clean_d}")
                else:
                    raw_lines.append(clean_d)
    if safe_date:
        raw_lines.append(f"Date: {safe_date}")
    if safe_reason:
        raw_lines.append(f"Reason: {safe_reason}")

    header_fontsize = min(h * 0.21, w * 0.12)
    max_chars = max([len(ln) for ln in raw_lines] + [24])
    body_fontsize = min(h * 0.105, (w * 1.82) / max_chars)
    
    page.insert_text(
        fitz.Point(x0 + 2, y0 + h * 0.225),
        "Signature valid",
        fontsize=header_fontsize,
        fontname="helv",
        color=(0, 0, 0)
    )
        
    start_y = y0 + h * 0.385
    line_gap = min(body_fontsize * 1.16, (h * 0.58) / max(len(raw_lines), 1))
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
        if st.session_state.get("last_uploaded_name") != uploaded_file.name:
            st.session_state["last_uploaded_name"] = uploaded_file.name
            st.session_state.pop("processed_pdf", None)

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
            auto_name, auto_desig, auto_date, auto_reason = extract_universal_signature_details(doc)

            st.info(
                f"✨ **PDF से स्वतः फेच किया गया सिग्नेचर विवरण:**\n"
                f"- **अधिकारी का नाम (Name):** `{auto_name}`\n"
                f"- **पद (Designation):** `{auto_desig.replace(chr(10), ' ') if auto_desig else 'N/A'}`\n"
                f"- **दिनांक व समय (Date):** `{auto_date if auto_date else 'N/A'}`\n"
                f"- **कारण (Reason):** `{auto_reason}`"
            )

            if st.button("🚀 सिग्नेचर वैलिडेट करें और सभी पेजों पर ग्रीन टिक (✔) लगाएं", use_container_width=True, key="s_btn"):
                out_doc = fitz.open("pdf", doc.tobytes())
                stamped_count = 0
                
                # लूप पूरे डॉक्यूमेंट के हर एक पेज पर चलेगा (मल्टी-पेज सपोर्ट)
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
                st.session_state["show_preview"] = True
                base_name = uploaded_file.name.rsplit(".", 1)[0]
                st.session_state["default_filename"] = f"{base_name}_Validated"

            if "processed_pdf" in st.session_state:
                st.success("✅ आपकी ग्रीन टिक वाली फाइल तैयार है!")
                
                if st.button("👁️ PDF व्यू (Preview) देखें / छुपाएं", use_container_width=True, key="s_prev"):
                    st.session_state["show_preview"] = not st.session_state.get("show_preview", False)
                    
                if st.session_state.get("show_preview", False):
                    st.info("📄 फाइल का प्रीव्यू (सभी पेज):")
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
                    b_name, b_desig, b_date, b_reason = extract_universal_signature_details(b_doc)
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
                    c_name, c_desig, c_date, c_reason = extract_universal_signature_details(c_doc)
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
                    s_name, s_desig, s_date, s_reason = extract_universal_signature_details(s_doc)
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
