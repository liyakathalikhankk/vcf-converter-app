import streamlit as st
import io, zipfile, re
import pandas as pd
import phonenumbers

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="VCF Converter Pro+",
    page_icon="📇",
    layout="wide"
)

st.title("📇 VCF Converter Pro+")
st.caption("TXT / CSV ⇄ VCF | Split | Merge | Analyze | Clean | Mobile-safe")

# =================================================
# HELPERS
# =================================================
def clean_raw_numbers(lines):
    return [
        str(l).replace("\ufeff", "").strip()
        for l in lines
        if l and str(l).strip().lower() not in ["nan", "none"]
    ]


def normalize_number(raw):
    raw = str(raw).strip()
    if not raw:
        return None

    digits = re.sub(r"\D", "", raw)
    try:
        if raw.startswith("+"):
            num = phonenumbers.parse(raw, None)
        else:
            num = phonenumbers.parse("+" + digits, None)

        # BULK-SAFE CHECK
        if phonenumbers.is_possible_number(num):
            return phonenumbers.format_number(
                num, phonenumbers.PhoneNumberFormat.E164
            )
    except:
        pass
    return None


def extract_numbers_from_vcf(content):
    nums = []
    for line in content.splitlines():
        if line.startswith("TEL"):
            nums.append(line.split(":")[-1].strip())
    return nums


def extract_contacts_from_vcf(content):
    contacts = []
    current_name = None
    numbers = []

    for line in content.splitlines():
        line = line.strip()
        if line.startswith("FN:"):
            current_name = line.replace("FN:", "").strip()
            numbers = []
        elif line.startswith("TEL"):
            numbers.append(line.split(":")[-1].strip())
        elif line == "END:VCARD" and current_name:
            contacts.append((current_name, numbers))
            current_name = None
            numbers = []

    return contacts


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


def merge_vcf_files(vcf_contents, merge_by_name=True, merge_by_number=True):
    merged = {}

    for content in vcf_contents:
        for name, nums in extract_contacts_from_vcf(content):
            nums = set(nums)
            if merge_by_name:
                merged.setdefault(name, set()).update(nums)
            else:
                merged[f"{name}_{len(merged)+1}"] = nums

    if merge_by_number:
        seen = set()
        for name in merged:
            merged[name] = {
                n for n in merged[name]
                if not (n in seen or seen.add(n))
            }

    lines = []
    for name, numbers in merged.items():
        if not numbers:
            continue
        lines.append("BEGIN:VCARD")
        lines.append("VERSION:3.0")
        lines.append(f"N:{name};;;;")
        lines.append(f"FN:{name}")
        for n in sorted(numbers):
            lines.append(f"TEL;TYPE=CELL:{n}")
        lines.append("END:VCARD")

    return "\n".join(lines)

# =================================================
# TABS
# =================================================
tabs = st.tabs([
    "🔁 TXT ➜ VCF",
    "📄 CSV ➜ VCF",
    "🔄 VCF ➜ TXT",
    "🧾 TXT ➜ CSV",
    "🧾 CSV ➜ TXT",
    "📂 Split Files",
    "🧩 VCF Merge",
    "🧹 Analyze & Clean"
])

# =================================================
# TXT ➜ VCF
# =================================================
with tabs[0]:
    txt_files = st.file_uploader("Upload TXT", type=["txt"], accept_multiple_files=True, key="t1_txt")
    manual = st.text_area("Or paste numbers", height=200, key="t1_paste")

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 1000, 50, key="t1_batch")
    set_start = c2.number_input("Set start number", 1, 10000, 1, key="t1_set")
    name_prefix = c3.text_input("Contact name prefix", "Contact", key="t1_name")
    file_prefix = c4.text_input("VCF file prefix", "Contacts", key="t1_file")

    if st.button("Convert TXT → VCF", key="t1_btn"):
        raw = []
        if txt_files:
            for f in txt_files:
                raw.extend(f.read().decode(errors="ignore").splitlines())
        if manual.strip():
            raw.extend(manual.splitlines())

        seen, ordered = set(), []
        for r in clean_raw_numbers(raw):
            n = normalize_number(r)
            if n and n not in seen:
                seen.add(n)
                ordered.append(n)

        if ordered:
            vcf = generate_vcf(ordered, name_prefix, file_prefix, set_start, batch)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for k, v in vcf.items():
                    z.writestr(k, v)
            buf.seek(0)
            st.download_button("Download VCF ZIP", buf, file_name=f"{file_prefix}.zip")

# =================================================
# CSV ➜ VCF
# =================================================
with tabs[1]:
    csv_file = st.file_uploader("Upload CSV", type=["csv"], key="t2_csv")

    c1, c2, c3, c4 = st.columns(4)
    batch = c1.number_input("Contacts per VCF", 1, 1000, 50, key="t2_batch")
    set_start = c2.number_input("Set start number", 1, 10000, 1, key="t2_set")
    name_prefix = c3.text_input("Contact name prefix", "Contact", key="t2_name")
    file_prefix = c4.text_input("VCF file prefix", "Contacts", key="t2_file")

    if csv_file and st.button("Convert CSV → VCF", key="t2_btn"):
        df = pd.read_csv(csv_file)
        col = next((c for c in df.columns if "phone" in c.lower()), None)
        if col:
            seen, ordered = set(), []
            for v in df[col].astype(str):
                n = normalize_number(v)
                if n and n not in seen:
                    seen.add(n)
                    ordered.append(n)

            vcf = generate_vcf(ordered, name_prefix, file_prefix, set_start, batch)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for k, v in vcf.items():
                    z.writestr(k, v)
            buf.seek(0)
            st.download_button("Download VCF ZIP", buf, file_name=f"{file_prefix}.zip")

# =================================================
# VCF ➜ TXT
# =================================================
with tabs[2]:
    vcf_files = st.file_uploader("Upload VCF", type=["vcf"], accept_multiple_files=True, key="t3_vcf")
    if vcf_files:
        nums = []
        for f in vcf_files:
            nums.extend(extract_numbers_from_vcf(f.read().decode(errors="ignore")))
        st.download_button("Download TXT", "\n".join(nums), file_name="contacts.txt")

# =================================================
# TXT ➜ CSV
# =================================================
with tabs[3]:
    f = st.file_uploader("Upload TXT", type=["txt"], key="t4_txt")
    if f:
        df = pd.DataFrame({"phone": clean_raw_numbers(f.read().decode(errors="ignore").splitlines())})
        st.download_button("Download CSV", df.to_csv(index=False), file_name="contacts.csv")

# =================================================
# CSV ➜ TXT
# =================================================
with tabs[4]:
    f = st.file_uploader("Upload CSV", type=["csv"], key="t5_csv")
    if f:
        df = pd.read_csv(f)
        st.download_button("Download TXT", "\n".join(df.iloc[:, 0].astype(str)), file_name="contacts.txt")

# =================================================
# SPLIT FILES
# =================================================
with tabs[5]:
    kind = st.radio("File type", ["TXT", "VCF"], key="t6_kind")

    if kind == "TXT":
        batch = st.number_input("Lines per TXT", 1, 100000, 100, key="t6_txt_batch")
        prefix = st.text_input("TXT file prefix", "Split", key="t6_txt_prefix")
        f = st.file_uploader("Upload TXT", type=["txt"], key="t6_txt")

        if f and st.button("Split TXT", key="t6_txt_btn"):
            lines = clean_raw_numbers(f.read().decode(errors="ignore").splitlines())
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for i in range(0, len(lines), batch):
                    z.writestr(f"{prefix} {i//batch+1}.txt", "\n".join(lines[i:i+batch]))
            buf.seek(0)
            st.download_button("Download ZIP", buf, file_name=f"{prefix}_txt_split.zip")

    else:
        batch = st.number_input("Contacts per VCF", 1, 1000, 100, key="t6_vcf_batch")
        set_start = st.number_input("Set start number", 1, 10000, 1, key="t6_vcf_set")
        name_prefix = st.text_input("Contact name prefix", "Contact", key="t6_vcf_name")
        prefix = st.text_input("VCF file prefix", "Contacts", key="t6_vcf_prefix")
        f = st.file_uploader("Upload VCF", type=["vcf"], key="t6_vcf")

        if f and st.button("Split & Rebuild VCF", key="t6_vcf_btn"):
            nums = extract_numbers_from_vcf(f.read().decode(errors="ignore"))
            vcf = generate_vcf(nums, name_prefix, prefix, set_start, batch)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
                for k, v in vcf.items():
                    z.writestr(k, v)
            buf.seek(0)
            st.download_button("Download ZIP", buf, file_name=f"{prefix}_vcf_split.zip")

# =================================================
# VCF MERGE
# =================================================
with tabs[6]:
    vcf_files = st.file_uploader("Upload multiple VCF files", type=["vcf"], accept_multiple_files=True, key="merge_vcf")
    merge_name = st.checkbox("Merge same contact name", True, key="merge_name")
    merge_number = st.checkbox("Remove duplicate phone numbers", True, key="merge_number")
    output = st.text_input("Output filename", "merged_contacts", key="merge_output")

    if vcf_files and st.button("Merge VCF"):
        contents = [f.read().decode(errors="ignore") for f in vcf_files]
        merged = merge_vcf_files(contents, merge_name, merge_number)
        st.download_button("Download Merged VCF", merged, file_name=f"{output}.vcf", mime="text/vcard")

# =================================================
# ANALYZE & CLEAN
# =================================================
with tabs[7]:
    f = st.file_uploader("Upload TXT or VCF", type=["txt", "vcf"], key="an_file")

    if f:
        content = f.read().decode(errors="ignore")
        is_vcf = f.name.lower().endswith(".vcf")

        nums = extract_numbers_from_vcf(content) if is_vcf else clean_raw_numbers(content.splitlines())
        norm = [normalize_number(n) for n in nums if normalize_number(n)]

        st.metric("Total entries", len(nums))
        st.metric("Unique numbers", len(set(norm)))
        st.metric("Duplicates", len(norm) - len(set(norm)))

        preview = "\n".join(content.splitlines()[:40 if is_vcf else 100])
        st.text_area("Preview", preview, height=200)

        new_name = st.text_input("Output filename (no extension)", f.name.split(".")[0], key="an_name")
        remove_dup = st.checkbox("Remove duplicates", True, key="an_dup")
        merge_same_name = st.checkbox("Merge contacts with same name (VCF)", False, key="an_merge")

        if is_vcf:
            prefix = st.text_input("New contact name prefix", "Contact", key="an_prefix")
            start = st.number_input("Set start number", 1, 10000, 1, key="an_set")

        if st.button("Process & Download", key="an_btn"):
            final = []
            seen = set()
            for n in norm:
                if not remove_dup or n not in seen:
                    seen.add(n)
                    final.append(n)

            if is_vcf:
                if merge_same_name:
                    out = merge_vcf_files([content], True, True)
                else:
                    vcf = generate_vcf(final, prefix, new_name, start, len(final))
                    out = list(vcf.values())[0]

                st.download_button("Download Clean VCF", out, file_name=f"{new_name}.vcf", mime="text/vcard")
            else:
                st.download_button("Download Clean TXT", "\n".join(final), file_name=f"{new_name}.txt", mime="text/plain")

# =================================================
# FOOTER
# =================================================
st.markdown("---")
st.info("🔐 Privacy Mode: All processing is local. No data is stored.")
st.markdown("Made by **Liyakath Ali Khan ✨**")
