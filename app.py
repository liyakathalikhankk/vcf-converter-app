# streamlit_vcf_converter.py
import streamlit as st
import os
import io
import zipfile
from datetime import datetime

st.set_page_config(page_title="VCF Converter", layout="wide")
st.title("📇 VCF Converter (TXT ➜ VCF)")

st.markdown("""
Convert plain phone numbers into VCF contact files. Works great on desktop and mobile!
""")

def clean_number(n):
    n = n.strip()
    if n and ((n.startswith('+') and n[1:].isdigit()) or n.isdigit()):
        return n if n.startswith('+') else '+' + n
    return None

def generate_vcf(contacts, name_prefix, set_start=1, batch_size=50):
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
        vcf_files[f"{name_prefix}_{set_start + set_num}.vcf"] = "\n".join(lines)
    return vcf_files

uploaded_files = st.file_uploader("📂 Upload TXT file(s) with phone numbers", type=["txt"], accept_multiple_files=True)

manual_input = st.text_area("✍️ Or Paste Numbers Here (one per line)", height=200)

col1, col2, col3 = st.columns(3)
with col1:
    prefix = st.text_input("🔤 Contact Name Prefix", value="Contact")
with col2:
    start_set = st.number_input("🔢 Start Set Number", value=1, min_value=1)
with col3:
    batch_size = st.number_input("📦 Contacts per VCF", value=50, min_value=1)

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
        vcf_dict = generate_vcf(contacts, prefix, set_start, batch_size)

        # Create ZIP archive in memory
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for filename, content in vcf_dict.items():
                zipf.writestr(filename, content)
        zip_buffer.seek(0)

        # Summary
        st.success(f"✅ Converted {len(contacts)} contacts into {len(vcf_dict)} VCF file(s)")
        st.download_button("📥 Download VCF ZIP", zip_buffer, file_name="vcf_contacts.zip", mime="application/zip")

        st.markdown("---")
        st.markdown("### 🔍 Summary")
        st.text(f"Total numbers entered      : {len(raw_numbers)}")
        st.text(f"Valid + unique contacts     : {len(contacts)}")
        st.text(f"VCF files generated         : {len(vcf_dict)}")
        st.text(f"Contacts per file           : {batch_size}")
        st.text(f"Contact name format         : {prefix} <set> <number>")
        st.text(f"Set numbering starts from   : {start_set}")
        st.markdown("---")

st.markdown("""
---
Made with ❤️ for mobile and desktop. Paste, upload, convert — done!
""")
