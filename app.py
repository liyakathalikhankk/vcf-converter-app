import sys
import subprocess

# ---- Failsafe for Streamlit Cloud ----
try:
    import phonenumbers
except ModuleNotFoundError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "phonenumbers"])
    import phonenumbers

import streamlit as st
import io, zipfile, re
import pandas as pd

# -------------------------------------------------
# PAGE CONFIG
# -------------------------------------------------
st.set_page_config(
    page_title="VCF Converter Pro+",
    page_icon="📇",
    layout="wide"
)

st.title("📇 VCF Converter Pro+")
st.caption("TXT / CSV ⇄ VCF | Auto country detection | Mobile-safe")

# -------------------------------------------------
# INPUT CLEANER
# -------------------------------------------------
def clean_raw_numbers(lines):
    cleaned = []
    for line in lines:
        if not line:
            continue
        line = str(line).replace("\ufeff", "").strip()
        if not line:
            continue
        if line.lower() in ["nan", "none"]:
            continue
        cleaned.append(line)
    return cleaned

# -------------------------------------------------
# UNIVERSAL NORMALIZER (ALL COUNTRIES)
# -------------------------------------------------
def normalize_number(raw):
    raw = str(raw).strip()
    if not raw or raw.lower() in ["nan", "none"]:
        return None

    digits = re.sub(r"\D", "", raw)

    # Case 1: already has +
    if raw.startswith("+"):
        try:
            num = phonenumbers.parse(raw, None)
            if phonenumbers.is_valid_number(num):
                return phonenumbers.format_number(
                    num, phonenumbers.PhoneNumberFormat.E164
                )
        except:
            return None

    # Case 2: no +, try adding +
    try:
        num = phonenumbers.parse("+" + digits, None)
        if phonenumbers.is_valid_number(num):
            return phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            )
    except:
        pass

    return None

# -------------------------------------------------
# VCF GENERATOR (ORDER + SET SAFE)
# -------------------------------------------------
def generate_vcf(numbers, name_prefix, file_prefix, set_start, batch_size):
    vcf_files = {}
    total_sets = (len(numbers) + batch_size - 1) // batch_size

    for s in range(total_sets):
        chunk = numbers[s * batch_size:(s + 1) * batch_size]
        set_no = set_start + s
        pad = len(str(len(chunk)))
        lines = []

        for i, num in enumerate(chunk, start=1):
            idx = str(i).zfill(pad)
            name = f"{name_prefix} {set_no} {idx}"

            lines.extend([
                "BEGIN:VCARD",
                "VERSION:3.0",
                f"N:{idx};{name_prefix} {set_no};;;",
                f"FN:{name}",
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
        key="txt_to_vcf"
    )

    manual = st.text_area(
        "Or paste numbers (with country code)",
        height=200,
        key="txt_paste"
    )

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 500, 50)
    set_start = c2.number_input("Set start number", 1, 10000, 1)
    name_prefix = c3.text_input("Contact name prefix", "Contact")
    file_prefix = c4.text_input("VCF file prefix", "Contacts")

    if st.button("🚀 Convert TXT → VCF"):
        raw = []

        if txt_files:
            for f in txt_files:
                raw.extend(f.read().decode(errors="ignore").splitlines())

        if manual.strip():
            raw.extend(manual.splitlines())

        raw = clean_raw_numbers(raw)

        seen, ordered, invalid = set(), [], 0

        for r in raw:
            num = normalize_number(r)
            if num:
                if num not in seen:
                    seen.add(num)
                    ordered.append(num)
            else:
                invalid += 1

        if not ordered:
            st.error("❌ No valid contacts found.")
        else:
            vcf_files = generate_vcf(
                ordered, name_prefix, file_prefix, set_start, batch
            )

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w") as z:
                for k, v in vcf_files.items():
                    z.writestr(k, v)
            buf.seek(0)

            st.download_button(
                "📥 Download VCF ZIP",
                buf,
                file_name=f"{file_prefix}.zip"
            )

            st.success(f"✅ Valid: {len(ordered)} | Skipped: {invalid}")

# =================================================
# CSV ➜ VCF
# =================================================
with tab2:
    csv_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        key="csv_to_vcf"
    )

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 500, 50, key="csv_batch")
    set_start = c2.number_input("Set start number", 1, 10000, 1, key="csv_set")
    name_prefix = c3.text_input("Contact name prefix", "Contact", key="csv_name")
    file_prefix = c4.text_input("VCF file prefix", "Contacts", key="csv_file")

    if csv_file and st.button("🚀 Convert CSV → VCF"):
        df = pd.read_csv(csv_file)
        phone_col = next(
            (c for c in df.columns if "phone" in c.lower() or "number" in c.lower()),
            None
        )

        if not phone_col:
            st.error("❌ No phone column found in CSV")
        else:
            seen, ordered, invalid = set(), [], 0

            for _, row in df.iterrows():
                num = normalize_number(str(row[phone_col]))
                if num:
                    if num not in seen:
                        seen.add(num)
                        ordered.append(num)
                else:
                    invalid += 1

            if not ordered:
                st.error("❌ No valid contacts found.")
            else:
                vcf_files = generate_vcf(
                    ordered, name_prefix, file_prefix, set_start, batch
                )

                buf = io.BytesIO()
                with zipfile.ZipFile(buf, "w") as z:
                    for k, v in vcf_files.items():
                        z.writestr(k, v)
                buf.seek(0)

                st.download_button(
                    "📥 Download VCF ZIP",
                    buf,
                    file_name=f"{file_prefix}.zip"
                )

                st.success(f"✅ Valid: {len(ordered)} | Skipped: {invalid}")

# =================================================
# VCF ➜ TXT
# =================================================
with tab3:
    vcf_files = st.file_uploader(
        "Upload VCF file(s)",
        type=["vcf"],
        accept_multiple_files=True,
        key="vcf_to_txt"
    )

    txt_name = st.text_input("Output TXT filename", "contacts", key="vcf_txt_name")

    if vcf_files:
        seen, ordered = set(), []

        for f in vcf_files:
            content = f.read().decode(errors="ignore").replace("\r\n", "\n")
            for line in content.splitlines():
                if line.startswith("TEL"):
                    num = line.split(":")[-1].strip()
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
    txt_file = st.file_uploader(
        "Upload TXT",
        type=["txt"],
        key="txt_to_csv"
    )
    if txt_file:
        lines = clean_raw_numbers(
            txt_file.read().decode(errors="ignore").splitlines()
        )
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
    csv_file = st.file_uploader(
        "Upload CSV",
        type=["csv"],
        key="csv_to_txt"
    )
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
    kind = st.radio("File type", ["TXT", "VCF"], key="split_type")
    size = st.number_input("Contacts per file", 1, 1000, 100, key="split_size")
    prefix = st.text_input("Output file prefix", "Split", key="split_prefix")

    if kind == "TXT":
        f = st.file_uploader(
            "Upload TXT",
            type=["txt"],
            key="split_txt"
        )
        if f:
            lines = clean_raw_numbers(
                f.read().decode(errors="ignore").splitlines()
            )
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
        f = st.file_uploader(
            "Upload VCF",
            type=["vcf"],
            key="split_vcf"
        )
        if f:
            content = f.read().decode(errors="ignore").replace("\r\n", "\n")
            cards = [
                c + "END:VCARD"
                for c in content.split("END:VCARD")
                if c.strip()
            ]
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
