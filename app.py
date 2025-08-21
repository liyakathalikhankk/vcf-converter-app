# app.py
import streamlit as st
import os
import io
import zipfile

st.set_page_config(page_title="VCF Converter", layout="wide")
st.title("📇 VCF Converter (TXT ⇄ VCF + Splitter)")

st.markdown("Convert and split contact numbers between .txt and .vcf formats. Mobile-ready, easy and fast!")

# -------------------------------
# Helper functions
# -------------------------------
def clean_number(n):
    n = n.strip()
    if n and ((n.startswith('+') and n[1:].isdigit()) or n.isdigit()):
        return n if n.startswith('+') else '+' + n
    return None

def generate_vcf(contacts, name_prefix, file_prefix, set_start=1, batch_size=50):
    vcf_files = {}
    total_contacts = len(contacts)
    total_sets = (total_contacts + batch_size - 1) // batch_size

    for set_num in range(total_sets):
        start_idx = set_num * batch_size
        end_idx = min((set_num + 1) * batch_size, total_contacts)
        subset = contacts[start_idx:end_idx]
        lines = []
        for i, num in enumerate(subset):
            name = f"{name_prefix} {set_start + set_num:02} {i + 1:03}"
            lines.append("BEGIN:VCARD")
            lines.append("VERSION:3.0")
            lines.append(f"N:{name};;;")
            lines.append(f"FN:{name}")
            lines.append(f"TEL;TYPE=CELL:{num}")
            lines.append("END:VCARD")
        vcf_files[f"{file_prefix}_{set_start + set_num}.vcf"] = "\n".join(lines)
    return vcf_files


# -------------------------------
# Tabs
# -------------------------------
tab1, tab2, tab3 = st.tabs(["🔁 TXT ➜ VCF", "🔄 VCF ➜ TXT", "📂 Split Files"])

# -------------------------------
# Tab 1: TXT ➜ VCF
# -------------------------------
with tab1:
    st.header("🔁 TXT ➜ VCF")

    uploaded_files = st.file_uploader("📂 Upload TXT file(s) with phone numbers", type=["txt"], accept_multiple_files=True)
    manual_input = st.text_area("✍️ Or Paste Numbers Here (one per line)", height=200)

    col1, col2, col3 = st.columns(3)
    with col1:
        contact_type = st.radio("Contact Type", ["General", "Admin", "Navy"])
    with col2:
        batch_size = st.number_input("📦 Contacts per VCF", value=50, min_value=1)
    with col3:
        set_start = st.number_input("🔢 Start Set Number", value=1, min_value=1)

    # Manual prefix entry for all types
    name_prefix = st.text_input("🔤 Contact Name Prefix (for FN/N field)", value=contact_type)
    file_prefix = st.text_input("📁 VCF Filename Prefix", value=f"{contact_type.lower()}_file")

    if st.button("🚀 Convert to VCF"):
        raw_numbers = []

        if uploaded_files:
            for file in uploaded_files:
                content = file.read().decode("utf-8")
                raw_numbers.extend(content.strip().splitlines())

        if manual_input.strip():
            raw_numbers.extend(manual_input.strip().splitlines())

        cleaned = [clean_number(n) for n in raw_numbers]
        contacts = sorted(set(filter(None, cleaned)), key=lambda x: int(x.replace('+', '').lstrip('0') or '0'))

        if not contacts:
            st.error("❌ No valid phone numbers found.")
        else:
            vcf_dict = generate_vcf(contacts, name_prefix, file_prefix, set_start, batch_size)
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for filename, content in vcf_dict.items():
                    zipf.writestr(filename, content)
            zip_buffer.seek(0)

            st.success(f"✅ Converted {len(contacts)} contacts into {len(vcf_dict)} VCF file(s)")
            st.download_button("📥 Download VCF ZIP", zip_buffer, file_name=f"{file_prefix}_contacts.zip", mime="application/zip")


# -------------------------------
# Tab 2: VCF ➜ TXT
# -------------------------------
with tab2:
    st.header("🔄 VCF ➜ TXT")

    vcf_files = st.file_uploader("📥 Upload one or more .vcf files", type=["vcf"], accept_multiple_files=True)
    custom_txt_name = st.text_input("📁 TXT Filename (no extension)", value="contacts")

    if vcf_files:
        numbers = []
        for vcf_file in vcf_files:
            content = vcf_file.read().decode("utf-8")
            lines = content.strip().splitlines()
            for line in lines:
                if line.startswith("TEL"):
                    number = line.split(":")[-1].strip()
                    number = ''.join(filter(str.isdigit, number))  # remove + and symbols
                    if number:
                        numbers.append(number)

        if numbers:
            txt_data = "\n".join(numbers)
            st.download_button("📤 Download TXT", txt_data, file_name=f"{custom_txt_name}.txt", mime="text/plain")
            st.success(f"✅ Extracted {len(numbers)} contacts from {len(vcf_files)} VCF file(s).")


# -------------------------------
# Tab 3: Split Files
# -------------------------------
with tab3:
    st.header("📂 Split Files")

    split_choice = st.radio("Choose file type to split", ["TXT", "VCF"])
    custom_prefix = st.text_input("📁 Custom Split Filename Prefix", value="split")

    if split_choice == "TXT":
        txt_file = st.file_uploader("📂 Upload TXT file", type=["txt"])
        split_size = st.number_input("Contacts per TXT split", value=100, min_value=1)
        if txt_file:
            content = txt_file.read().decode("utf-8")
            lines = content.strip().splitlines()
            chunks = [lines[i:i+split_size] for i in range(0, len(lines), split_size)]

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for idx, chunk in enumerate(chunks, 1):
                    zipf.writestr(f"{custom_prefix}_{idx}.txt", "\n".join(chunk))
            zip_buffer.seek(0)

            st.download_button("📥 Download Split TXT ZIP", zip_buffer, file_name=f"{custom_prefix}_txt_files.zip", mime="application/zip")
            st.success(f"✅ Split into {len(chunks)} TXT files")

    elif split_choice == "VCF":
        vcf_file = st.file_uploader("📂 Upload VCF file", type=["vcf"])
        split_size = st.number_input("Contacts per VCF split", value=100, min_value=1)
        if vcf_file:
            content = vcf_file.read().decode("utf-8")
            vcards = content.split("END:VCARD")
            vcards = [v.strip()+"\nEND:VCARD" for v in vcards if v.strip()]
            chunks = [vcards[i:i+split_size] for i in range(0, len(vcards), split_size)]

            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                for idx, chunk in enumerate(chunks, 1):
                    zipf.writestr(f"{custom_prefix}_{idx}.vcf", "\n".join(chunk))
            zip_buffer.seek(0)

            st.download_button("📥 Download Split VCF ZIP", zip_buffer, file_name=f"{custom_prefix}_vcf_files.zip", mime="application/zip")
            st.success(f"✅ Split into {len(chunks)} VCF files")


st.markdown("---\nMade by **Liyakath Ali Khan ✨** | Mobile-ready VCF tool | Streamlit-powered")
