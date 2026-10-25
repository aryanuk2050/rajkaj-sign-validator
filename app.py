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
st.caption("पूरे भारत और राजस्थान (राजकाज, ई-आधार, ई-मित्र व सभी विभागीय आदेशों) के लिए ऑटोमैटिक पीडीएफ सॉल्यूशन")

# -------------------- UNIVERSAL HINDI-TO-ENGLISH ENGINE --------------------
# यह डिक्शनरी किसी व्यक्ति के लिए नहीं, बल्कि पूरे भारत के प्रशासनिक पदों के सटीक अनुवाद के लिए है

ADMIN_VOCAB = {
    "कार्यालय": "Office of",
    "जिला निर्वाचन अधिकारी": "District Election Officer",
    "निर्वाचक रजिस्ट्रीकरण पदाधिकारी": "Electoral Registration Officer",
    "उप जिला निर्वाचन अधिकारी": "Deputy District Election Officer",
    "अतिरिक्त जिला कलक्टर": "Additional District Collector",
    "अतिरिक्त जिला कलेक्टर": "Additional District Collector",
    "जिला कलक्टर एवं जिला मजिस्ट्रेट": "District Collector & Magistrate",
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
    "अतिरिक्त मुख्य कार्यकारी अधिकारी": "Additional Chief Executive Officer",
    "प्रमुख शासन सचिव": "Principal Secretary",
    "अतिरिक्त मुख्य सचिव": "Additional Chief Secretary",
    "मुख्य सचिव": "Chief Secretary",
    "शासन सचिव": "Secretary to Government",
    "संयुक्त शासन सचिव": "Joint Secretary",
    "उप शासन सचिव": "Deputy Secretary",
    "निदेशक": "Director",
    "अतिरिक्त निदेशक": "Additional Director",
    "संयुक्त निदेशक": "Joint Director",
    "उप निदेशक": "Deputy Director",
    "सहायक निदेशक": "Assistant Director",
    "मुख्य अभियंता": "Chief Engineer",
    "अतिरिक्त मुख्य अभियंता": "Additional Chief Engineer",
    "अधीक्षण अभियंता": "Superintending Engineer",
    "अधिशाषी अभियंता": "Executive Engineer",
    "सहायक अभियंता": "Assistant Engineer",
    "कनिष्ठ अभियंता": "Junior Engineer",
    "मुख्य जिला शिक्षा अधिकारी": "Chief District Education Officer",
    "जिला शिक्षा अधिकारी": "District Education Officer",
    "ब्लॉक शिक्षा अधिकारी": "Block Education Officer",
    "प्रधानाचार्य": "Principal",
    "प्रधानाध्यापक": "Headmaster",
    "मुख्य चिकित्सा एवं स्वास्थ्य अधिकारी": "Chief Medical & Health Officer",
    "प्रमुख चिकित्सा अधिकारी": "Principal Medical Officer",
    "चिकित्सा अधिकारी": "Medical Officer",
    "पुलिस अधीक्षक": "Superintendent of Police",
    "अतिरिक्त पुलिस अधीक्षक": "Additional Superintendent of Police",
    "उप अधीक्षक पुलिस": "Deputy Superintendent of Police",
    "थानाधिकारी": "Station House Officer",
    "कोषाधिकारी": "Treasury Officer",
    "लेखाधिकारी": "Accounts Officer",
    "सहायक लेखाधिकारी": "Assistant Accounts Officer",
    "आयुक्त": "Commissioner",
    "अतिरिक्त आयुक्त": "Additional Commissioner",
    "संयुक्त आयुक्त": "Joint Commissioner",
    "उपायुक्त": "Deputy Commissioner",
    "सहायक आयुक्त": "Assistant Commissioner",
    "पंजीयक": "Registrar",
    "उप पंजीयक": "Sub Registrar",
    "पटवारी": "Patwari",
    "ग्राम विकास अधिकारी": "Village Development Officer",
    "प्रभारी अधिकारी": "Officer In-Charge",
    "नियंत्रण अधिकारी": "Controlling Officer",
    "आहरण एवं वितरण अधिकारी": "Drawing & Disbursing Officer",
    "पंचायत समिति": "Panchayat Samiti",
    "जिला परिषद": "Zila Parishad",
    "नगर निगम": "Municipal Corporation",
    "नगर परिषद": "Municipal Council",
    "नगर पालिका": "Municipality",
    "पंचायत": "Panchayat",
    "प्रकोष्ठ": "Cell",
    "विभाग": "Department",
    "अनुभाग": "Section",
    "मण्डल": "Division",
    "संभाग": "Division",
    "संभागीय": "Divisional",
    "ग्रामीण": "Rural",
    "शहरी": "Urban",
    "मुख्यालय": "Headquarters",
    "राजस्थान": "Rajasthan",
    "सरकार": "Government",
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
    """किसी भी हिंदी शब्द या अधिकारी के नाम को फोनेटिक अंग्रेजी (ASCII) में बदलना ताकि PDF में कभी '...' न बने"""
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

    # संयुक्त व्यंजन सुधार (जैसे न्द -> nd, न्य -> ny)
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
                # शब्द के अंतिम अक्षर में अनावश्यक 'a' न लगाएं
                next_is_dev = (i + 1 < n) and ('\u0900' <= res[i + 1] <= '\u097F')
                if not next_is_dev:
                    out.append(base)
                else:
                    out.append(base + 'a')
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


# -------------------- UNIVERSAL MULTI-LAYER PDF EXTRACTOR --------------------

def is_clean_value(val):
    if not val or len(val.strip()) < 2:
        return False
    low = val.lower().strip()
    junk = [
        "itext", "agpl", "version", "adobe", "pkcs7", "subfilter", "adbe",
        "sha256", "signing", "unknown", "null", "none", "signature", "valid"
    ]
    return not any(j in low for j in junk)

def is_ca_or_system_name(val):
    low = val.lower()
    ca_keywords = [
        "certifying authority", "ca 20", "sub ca", "root ca", "emudhra",
        "nic sub-ca", "cdac", "ncode", "capricorn", "sify", "verasys",
        "csc e-governance", "protean", "nsdl", "c-dac"
    ]
    return any(k in low for k in ca_keywords)

def extract_universal_signature_details(doc):
    """
    किसी भी राज्य/विभाग की PDF से 4 स्तरों पर जांच करके असली नाम, पद, दिनांक और कारण निकालना:
    स्तर 1: सिग्नेचर बॉक्स के अंदर मौजूद विज़ुअल टेक्स्ट (यदि पीडीएफ में छपा हो)
    स्तर 2: PKCS#7 डिजिटल सर्टिफिकेट चेन के सभी सर्टिफिकेट्स (End-Entity Signer Certificate)
    स्तर 3: PDF सिग्नेचर डिक्शनरी (/Name, /Reason, /Location, /M)
    स्तर 4: डॉक्यूमेंट के लेआउट में हस्ताक्षर ब्लॉक (जैसे कोष्ठक में लिखा अधिकारी का नाम व नीचे लिखा पद)
    """
    found_name = ""
    found_desig = ""
    found_loc = ""
    found_date = ""
    found_reason = ""
    issuer_info = ""

    # ---- स्तर 1, 2 और 3: सिग्नेचर विजेट और सर्टिफिकेट की जांच ----
    for page in doc:
        for widget in page.widgets():
            if widget.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                # 1A. सिग्नेचर बॉक्स के एरिया में पहले से मौजूद टेक्स्ट को पढ़ना
                try:
                    box_text = page.get_text("text", clip=widget.rect)
                    for bline in box_text.splitlines():
                        bline_clean = bline.strip()
                        if re.search(r'(?i)digitally\s+signed\s+by', bline_clean):
                            cand = re.sub(r'(?i).*?digitally\s+signed\s+by\s*:?\s*', '', bline_clean).strip()
                            if is_clean_value(cand) and not is_ca_or_system_name(cand):
                                found_name = cand
                        elif re.search(r'(?i)designation\s*:', bline_clean):
                            cand = re.sub(r'(?i).*?designation\s*:\s*', '', bline_clean).strip()
                            if is_clean_value(cand):
                                found_desig = cand
                        elif re.search(r'(?i)date\s*:', bline_clean):
                            cand = re.sub(r'(?i).*?date\s*:\s*', '', bline_clean).strip()
                            if len(cand) > 6:
                                found_date = cand
                        elif re.search(r'(?i)reason\s*:', bline_clean):
                            cand = re.sub(r'(?i).*?reason\s*:\s*', '', bline_clean).strip()
                            if is_clean_value(cand):
                                found_reason = cand
                        elif re.search(r'(?i)location\s*:', bline_clean):
                            cand = re.sub(r'(?i).*?location\s*:\s*', '', bline_clean).strip()
                            if is_clean_value(cand):
                                found_loc = cand
                except Exception:
                    pass

                # 1B. सिग्नेचर ऑब्जेक्ट और उसके /V रेफरेंस को पढ़ना
                sig_obj_str = doc.xref_object(widget.xref)
                v_match = re.search(r'/V\s+(\d+)\s+0\s+R', sig_obj_str)
                if v_match:
                    try:
                        sig_obj_str += "\n" + doc.xref_object(int(v_match.group(1)))
                    except Exception:
                        pass

                # Appearance Stream (XObject) के अंदर छुपे टेक्स्ट को भी चेक करना
                ap_refs = re.findall(r'(\d+)\s+0\s+R', sig_obj_str)
                for ref_str in ap_refs[:8]:
                    try:
                        s_bytes = doc.xref_stream(int(ref_str))
                        if s_bytes:
                            s_txt = s_bytes.decode('latin1', errors='ignore')
                            for p_match in re.findall(r'\(([^()]{3,120})\)', s_txt):
                                p_clean = p_match.replace('\\(', '(').replace('\\)', ')').strip()
                                if "digitally signed by" in p_clean.lower() and not found_name:
                                    cand = re.sub(r'(?i).*?digitally\s+signed\s+by\s*:?\s*', '', p_clean).strip()
                                    if is_clean_value(cand) and not is_ca_or_system_name(cand):
                                        found_name = cand
                                elif "designation" in p_clean.lower() and not found_desig:
                                    cand = re.sub(r'(?i).*?designation\s*:\s*', '', p_clean).strip()
                                    if is_clean_value(cand) and cand.lower() not in ("doit", "null"):
                                        found_desig = cand
                    except Exception:
                        pass

                # 2. PKCS#7 सर्टिफिकेट चेन के सभी सर्टिफिकेट्स की जांच
                contents_match = re.search(r'/Contents\s*<([0-9A-Fa-f\s]+)>', sig_obj_str)
                if contents_match:
                    try:
                        hex_data = re.sub(r'\s+', '', contents_match.group(1)).rstrip('0')
                        if len(hex_data) % 2 != 0:
                            hex_data += '0'
                        der_bytes = bytes.fromhex(hex_data)
                        certs = pkcs7.load_der_pkcs7_certificates(der_bytes)
                        
                        # सभी सर्टिफिकेट्स में से End-User (Signer) का सर्टिफिकेट ढूँढें
                        for cert in certs:
                            cn, title, ou, org, state, given = "", "", "", "", "", ""
                            for attr in cert.subject:
                                val = attr.value.strip() if isinstance(attr.value, str) else ""
                                if attr.oid == x509.NameOID.COMMON_NAME:
                                    cn = val
                                elif attr.oid == x509.NameOID.GIVEN_NAME:
                                    given = val
                                elif attr.oid == x509.NameOID.TITLE:
                                    title = val
                                elif attr.oid == x509.NameOID.ORGANIZATIONAL_UNIT_NAME:
                                    ou = val
                                elif attr.oid == x509.NameOID.ORGANIZATION_NAME:
                                    org = val
                                elif attr.oid == x509.NameOID.STATE_OR_PROVINCE_NAME:
                                    state = val

                            # यदि यह CA का सर्टिफिकेट नहीं है, तो यह असली हस्ताक्षरकर्ता का सर्टिफिकेट है!
                            if cn and not is_ca_or_system_name(cn) and is_clean_value(cn):
                                found_name = cn
                                if title and is_clean_value(title):
                                    found_desig = title
                                elif ou and is_clean_value(ou) and ou.lower() not in ("doit", "personal", "individual", "class 2", "class 3"):
                                    found_desig = ou
                                elif org and is_clean_value(org) and not is_ca_or_system_name(org) and org.lower() not in ("doit", "personal", "india"):
                                    found_desig = org
                                if state and not found_loc:
                                    found_loc = state
                            elif given and not found_name and is_clean_value(given):
                                found_name = given
                    except Exception:
                        pass

                # 3. PDF Dictionary Fields (/Name, /Reason, /Location, /M)
                if not found_reason:
                    r_m = re.search(r'/Reason\s*\((.*?)\)', sig_obj_str)
                    if r_m and is_clean_value(r_m.group(1)):
                        found_reason = r_m.group(1).strip()

                if not found_loc:
                    l_m = re.search(r'/Location\s*\((.*?)\)', sig_obj_str)
                    if l_m and is_clean_value(l_m.group(1)):
                        found_loc = l_m.group(1).strip()

                if not found_date:
                    d_m = re.search(r'/M\s*\(D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', sig_obj_str)
                    if d_m:
                        y, m, d, hh, mm, ss = d_m.groups()
                        found_date = f"{y}.{m}.{d} {hh}:{mm}:{ss} IST"

                if not found_name:
                    n_m = re.search(r'/Name\s*\((.*?)\)', sig_obj_str)
                    if n_m and is_clean_value(n_m.group(1)) and not is_ca_or_system_name(n_m.group(1)):
                        found_name = n_m.group(1).strip()

    # ---- स्तर 4: डॉक्यूमेंट के अंदर लिखे सिग्नेचर ब्लॉक (Document Layout) से नाम और पद निकालना ----
    # (जब PDF में iText की वजह से सर्टिफिकेट में नाम न हो या पद केवल लेटर में छपा हो)
    doc_name = ""
    doc_desig = ""
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"

    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    
    # पैटर्न A: कोष्ठक में लिखा अधिकारी का नाम, जैसे "(संदेश नायक)" या "(डॉ. राजेश शर्मा)" या "(R. K. Sharma)"
    non_person_words = [
        "कलक्टर", "कलेक्टर", "पंचायत", "आदेश", "जयपुर", "जोधपुर", "उदयपुर", "अजमेर", "कोटा",
        "बीकानेर", "भरतपुर", "राजस्थान", "प्रभारी", "महोदय", "समस्त", "जिला", "कार्यालय",
        "विभाग", "समिति", "परिषद", "निगम", "योजना", "प्रकोष्ठ", "शाखा", "अनुभाग", "पीआरओ",
        "collector", "office", "order", "department", "section", "jaipur", "rajasthan"
    ]
    
    for idx, ln in enumerate(lines):
        m = re.match(r'^\(\s*([औ-ज्ञअ-हA-Za-z\.\s]{3,42})\s*\)$', ln)
        if m:
            cand_name = m.group(1).strip()
            if not any(w in cand_name.lower() for w in non_person_words):
                doc_name = cand_name
                # नाम के ठीक नीचे की 1-2 लाइनों में अधिकारी का पद लिखा होता है
                d_parts = []
                for next_i in range(idx + 1, min(idx + 3, len(lines))):
                    nxt_line = lines[next_i]
                    if any(stop in nxt_line for stop in ["क्रमांक", "दिनांक", "प्रतिलिपि", "1.", "2.", "RajKaj", "Signature", "तेल", "फोन", "ईमेल"]):
                        break
                    d_parts.append(nxt_line)
                if d_parts:
                    doc_desig = "\n".join(d_parts)
                break

    # पैटर्न B: यदि कोष्ठक में नाम न हो, पर "आज्ञा से" या "भवदीय" या "दिनांक- यथा ई हस्ताक्षर" के पास पद लिखा हो
    if not doc_desig:
        for idx, ln in enumerate(lines):
            if "यथा ई हस्ताक्षर" in ln or "ई-हस्ताक्षर" in ln:
                # इसके ऊपर की 1-2 लाइनें देखें
                prev_parts = []
                for p_i in range(max(0, idx - 2), idx):
                    p_line = lines[p_i]
                    if len(p_line) < 55 and not any(st_w in p_line for st_w in ["क्रमांक", "प्रतिलिपि", "विषय", "संदर्भ"]):
                        prev_parts.append(p_line)
                if prev_parts:
                    doc_desig = "\n".join(prev_parts)
                break

    # ---- चारों स्तरों के परिणामों को मिलाकर सबसे सटीक डेटा चुनना ----
    final_name_raw = found_name if found_name else doc_name
    final_desig_raw = found_desig if (found_desig and found_desig.lower() != "doit") else (doc_desig if doc_desig else found_loc)

    # अंग्रेजी (ASCII) में बदलना ताकि PDF के Helvetica फॉन्ट में कभी '...' न छपे
    final_name = to_clean_english(final_name_raw) if final_name_raw else "Authorized Signatory"
    final_desig = to_clean_english(final_desig_raw) if final_desig_raw else ""
    final_date = found_date if found_date else ""
    final_reason = to_clean_english(found_reason) if found_reason else "Approved"

    return final_name, final_desig, final_date, final_reason


# -------------------- GREEN TICK & TEXT RENDERER --------------------

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

    # पुराने क्वेश्चन मार्क (?) को साफ करना
    page.draw_rect(rect, color=(1, 1, 1), fill=(1, 1, 1))
    
    w, h = rect.width, rect.height
    x0, y0 = rect.x0, rect.y0

    t_left = 0.032
    t_right = 0.039

    # Adobe Reader जैसा सटीक ग्रीन टिक
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

    header_fontsize = min(h * 0.205, w * 0.12)
    max_chars = max([len(ln) for ln in raw_lines] + [24])
    body_fontsize = min(h * 0.102, (w * 1.78) / max_chars)
    
    page.insert_text(
        fitz.Point(x0 + 2, y0 + h * 0.22),
        "Signature valid",
        fontsize=header_fontsize,
        fontname="helv",
        color=(0, 0, 0)
    )
        
    start_y = y0 + h * 0.375
    line_gap = min(body_fontsize * 1.16, (h * 0.59) / max(len(raw_lines), 1))
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
    uploaded_file = st.file_uploader("यहाँ किसी भी अधिकारी/विभाग की PDF फाइल चुनें", type=["pdf"], key="single_pdf")

    if uploaded_file:
        # नई फाइल अपलोड होने पर पुराना सेशन डेटा रिसेट करें
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
                f"🔍 **PDF से स्वतः प्राप्त सिग्नेचर विवरण:**\n"
                f"- **अधिकारी / संस्था (Signed by):** `{auto_name}`\n"
                f"- **पद / विभाग (Designation):** `{auto_desig.replace(chr(10), ' ') if auto_desig else 'N/A'}`\n"
                f"- **दिनांक व समय (Date):** `{auto_date if auto_date else 'N/A'}`\n"
                f"- **कारण (Reason):** `{auto_reason}`"
            )

            with st.expander("✏️ यदि आप नाम या पद में कुछ सुधार करना चाहें तो यहाँ क्लिक करें (वैकल्पिक)"):
                auto_name = st.text_input("अधिकारी का नाम (Name):", value=auto_name, key=f"n_{uploaded_file.name}")
                auto_desig = st.text_area("पद (Designation):", value=auto_desig, height=68, key=f"d_{uploaded_file.name}")
                auto_date = st.text_input("दिनांक व समय (Date):", value=auto_date, key=f"dt_{uploaded_file.name}")
                auto_reason = st.text_input("कारण (Reason):", value=auto_reason, key=f"r_{uploaded_file.name}")

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
                st.session_state["show_preview"] = True
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
    st.write("अलग-अलग अधिकारियों या विभागों की कितनी भी फाइलें अपलोड करें, यह हर फाइल से उसी के अधिकारी का नाम पढ़कर ग्रीन टिक लगाएगा।")
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
