import streamlit as st
import io, zipfile, re
import phonenumbers
import pandas as pd
from collections import Counter

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="VCF Converter Pro+",
    page_icon="📇",
    layout="wide"
)

st.title("📇 VCF Converter Pro+")
st.caption("TXT / CSV ⇄ VCF | TXT ⇄ CSV | Mobile Order Safe")

# -------------------------------------------------
# COUNTRY DETECTION
# -------------------------------------------------
COUNTRY_MAP = {
    "971": "AE", "966": "SA", "91": "IN",
    "1": "US", "44": "GB", "62": "ID",
    "60": "MY", "63": "PH"
}

def detect_country(raw):
    digits = re.sub(r"\D", "", raw)
    for code in sorted(COUNTRY_MAP, key=len, reverse=True):
        if digits.startswith(code):
            return COUNTRY_MAP[code]
    return "IN"

def normalize_number(raw):
    raw = str(raw).strip()
    if not raw:
        return None, None
    try:
        region = detect_country(raw)
        num = phonenumbers.parse(
            raw if raw.startswith("+") else raw,
            None if raw.startswith("+") else region
        )
        if phonenumbers.is_valid_number(num):
            return (
                phonenumbers.format_number(num, phonenumbers.PhoneNumberFormat.E164),
                phonenumbers.region_code_for_number(num)
            )
    except:
        pass
    return None, None

# -------------------------------------------------
# VCF GENERATOR (SET-BASED + MOBILE SAFE)
# -------------------------------------------------
def generate_vcf(numbers, name_prefix, file_prefix, set_start, batch_size):
    vcf_files = {}
    total_sets = (len(numbers) + batch_size - 1) // batch_size

    for s in range(total_sets):
        chunk = numbers[s * batch_size : (s + 1) * batch_size]
        set_no = set_start + s
        pad = len(str(len(chunk)))
        lines = []

        for i, num in enumerate(chunk, start=1):
            idx = str(i).zfill(pad)
            full_name = f"{name_prefix} {set_no} {idx}"

            lines.extend([
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"N:{idx};{name_prefix} {set_no};;;",
                f"FN:{full_name}",
                f"TEL;TYPE=CELL:{num}",
                "END:VCARD"
            ])

        vcf_files[f"{file_prefix} {set_no}.vcf"] = "\n".join(lines)

    return vcf_files

# -------------------------------------------------
# TABS
# -------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔁 TXT ➜ VCF",
    "📄 CSV ➜ VCF",
    "🔄 VCF ➜ TXT",
    "🧾 TXT ➜ CSV",
    "🧾 CSV ➜ TXT",
    "📂 Split Files"
])

# =================================================
# TXT ➜ VCF
# =================================================
with tab1:
    txt_files = st.file_uploader(
        "Upload TXT file(s)",
        type=["txt"],
        accept_multiple_files=True,
        key="txt_vcf"
    )

    manual = st.text_area("Or paste numbers", height=200)

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 500, 50)
    set_start = c2.number_input("Set start number", 1, 10000, 1)
    name_prefix_txt = c3.text_input("Contact name prefix", "Contact")
    file_prefix = c4.text_input("VCF file prefix", "Contacts")

    if st.button("🚀 Convert TXT → VCF"):
        raw = []
        if txt_files:
            for f in txt_files:
                raw.extend(f.read().decode().splitlines())
        if manual.strip():
            raw.extend(manual.splitlines())

        seen, ordered, invalid, countries = set(), [], 0, []

        for r in raw:
            num, country = normalize_number(r)
            if num:
                if num not in seen:
                    seen.add(num)
                    ordered.append(num)
                    countries.append(country)
            else:
                invalid += 1

        if ordered:
            vcf_files = generate_vcf(
                ordered, name_prefix_txt, file_prefix, set_start, batch
            )

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for k, v in vcf_files.items():
                    z.writestr(k, v)
            buf.seek(0)

            st.download_button("📥 Download VCF ZIP", buf, file_name=f"{file_prefix}.zip")
            st.success(f"Valid: {len(ordered)} | Invalid: {invalid}")

            df = pd.DataFrame(Counter(countries).items(), columns=["Country", "Count"])
            st.bar_chart(df.set_index("Country"))

# =================================================
# CSV ➜ VCF (SAME FEATURES)
# =================================================
with tab2:
    csv_file = st.file_uploader(
        "Upload CSV file",
        type=["csv"],
        key="csv_vcf"
    )

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 500, 50, key="csv_batch")
    set_start = c2.number_input("Set start number", 1, 10000, 1, key="csv_set")
    name_prefix_csv = c3.text_input("Contact name prefix", "Contact", key="csv_prefix")
    file_prefix = c4.text_input("VCF file prefix", "Contacts", key="csv_file_prefix")

    if csv_file and st.button("🚀 Convert CSV → VCF"):
        df = pd.read_csv(csv_file)
        phone_col = next(
            (c for c in df.columns if "phone" in c.lower() or "number" in c.lower()),
            None
        )

        if not phone_col:
            st.error("No phone column found in CSV")
        else:
            seen, ordered, invalid, countries = set(), [], 0, []

            for _, row in df.iterrows():
                num, country = normalize_number(row[phone_col])
                if num:
                    if num not in seen:
                        seen.add(num)
                        ordered.append(num)
                        countries.append(country)
                else:
                    invalid += 1

            vcf_files = generate_vcf(
                ordered, name_prefix_csv, file_prefix, set_start, batch
            )

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for k, v in vcf_files.items():
                    z.writestr(k, v)
            buf.seek(0)

            st.download_button("📥 Download VCF ZIP", buf, file_name=f"{file_prefix}.zip")
            st.success(f"Valid: {len(ordered)} | Invalid: {invalid}")

            dfc = pd.DataFrame(Counter(countries).items(), columns=["Country", "Count"])
            st.bar_chart(dfc.set_index("Country"))

# =================================================
# VCF ➜ TXT
# =================================================
with tab3:
    vcf_files = st.file_uploader(
        "Upload VCF file(s)",
        type=["vcf"],
        accept_multiple_files=True,
        key="vcf_txt"
    )

    txt_name = st.text_input("Output TXT filename", "contacts")

    if vcf_files:
        seen, ordered = set(), []
        for f in vcf_files:
            content = f.read().decode(errors="ignore").replace("\r\n", "\n")
            for line in content.splitlines():
                m = re.search(r"TEL[^:]*:(.+)", line)
                if m:
                    num = m.group(1).strip()
                    if num not in seen:
                        seen.add(num)
                        ordered.append(num)

        st.download_button(
            "📤 Download TXT",
            "\n".join(ordered),
            file_name=f"{txt_name}.txt"
        )

# =================================================
# TXT ➜ CSV
# =================================================
with tab4:
    txt_file = st.file_uploader("Upload TXT file", type=["txt"], key="txt_csv")
    if txt_file:
        lines = txt_file.read().decode().splitlines()
        df = pd.DataFrame({"phone": lines})
        st.download_button(
            "📥 Download CSV",
            df.to_csv(index=False),
            file_name="contacts.csv"
        )

# =================================================
# CSV ➜ TXT
# =================================================
with tab5:
    csv_file = st.file_uploader("Upload CSV file", type=["csv"], key="csv_txt")
    if csv_file:
        df = pd.read_csv(csv_file)
        col = df.columns[0]
        st.download_button(
            "📥 Download TXT",
            "\n".join(df[col].astype(str)),
            file_name="contacts.txt"
        )

# =================================================
# SPLITTER
# =================================================
with tab6:
    kind = st.radio("File type", ["TXT", "VCF"])
    size = st.number_input("Contacts per file", 1, 1000, 100)
    prefix = st.text_input("Output file prefix", "Split")

    if kind == "TXT":
        f = st.file_uploader("Upload TXT", type=["txt"], key="split_txt")
        if f:
            lines = f.read().decode().splitlines()
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for i in range(0, len(lines), size):
                    z.writestr(
                        f"{prefix} {i//size+1}.txt",
                        "\n".join(lines[i:i+size])
                    )
            buf.seek(0)
            st.download_button("📥 Download ZIP", buf)

    else:
        f = st.file_uploader("Upload VCF", type=["vcf"], key="split_vcf")
        if f:
            content = f.read().decode().replace("\r\n", "\n")
            cards = [c + "END:VCARD" for c in content.split("END:VCARD") if c.strip()]
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for i in range(0, len(cards), size):
                    z.writestr(
                        f"{prefix} {i//size+1}.vcf",
                        "\n".join(cards[i:i+size])
                    )
            buf.seek(0)
            st.download_button("📥 Download ZIP", buf)

# -------------------------------------------------
# FOOTER
# -------------------------------------------------
st.markdown("---")
st.info("🔐 Privacy Mode: All processing is local. No data is stored.")
st.markdown("Made by **Liyakath Ali Khan ✨**")
