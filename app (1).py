import streamlit as st
import requests
import json
import time
import xml.etree.ElementTree as ET
from xml.dom import minidom

# --- 1. FUNGSI KONVERSI JSON KE BPMN XML ---
def generate_bpmn_xml_string(json_data):
    bpmn_ns = "http://www.omg.org/spec/BPMN/20100524/MODEL"
    ET.register_namespace('bpmn', bpmn_ns)
    
    definitions = ET.Element("{%s}definitions" % bpmn_ns, id="Definitions_1")
    process = ET.SubElement(definitions, "{%s}process" % bpmn_ns, id="Process_1", isExecutable="true")
    
    for node in json_data.get("nodes", []):
        ET.SubElement(process, "{%s}%s" % (bpmn_ns, node["type"]), id=node["id"], name=node["name"])
        
    for i, edge in enumerate(json_data.get("edges", [])):
        flow_id = f"Flow_{i}"
        ET.SubElement(process, "{%s}sequenceFlow" % bpmn_ns, id=flow_id, sourceRef=edge["source"], targetRef=edge["target"])
        
    xml_string = ET.tostring(definitions, 'utf-8')
    pretty_xml = minidom.parseString(xml_string).toprettyxml(indent="  ")
    return pretty_xml

# --- 2. FUNGSI PEMANGGILAN API GEMINI ---
def ekstrak_ide_ke_json(api_key, ide_bisnis):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"
    
    prompt_system = """Anda adalah analis sistem. Ubah deskripsi ide bisnis menjadi JSON yang merepresentasikan proses operasional.
    Format JSON harus tepat seperti ini:
    {
      "process_name": "Nama Proses",
      "actors": ["Aktor 1", "Aktor 2"],
      "nodes": [
        {"id": "start_1", "type": "startEvent", "actor": "Klien", "name": "Mulai"},
        {"id": "task_1", "type": "task", "actor": "Admin", "name": "Deskripsi tugas"}
      ],
      "edges": [
        {"source": "start_1", "target": "task_1"}
      ]
    }
    Keluarkan HANYA JSON yang valid, tanpa teks awalan atau akhiran."""
    
    payload = {
        "contents": [{"parts": [{"text": prompt_system + "\n\nIde Bisnis:\n" + ide_bisnis}]}]
    }
    
    # Auto-retry maksimal 3 kali jika server penuh
    for percobaan in range(3):
        hasil = requests.post(url, headers={'Content-Type': 'application/json'}, json=payload)
        
        if hasil.status_code == 200:
            teks_output = hasil.json()['candidates'][0]['content']['parts'][0]['text']
            teks_bersih = teks_output.replace("```json", "").replace("```", "").strip()
            return json.loads(teks_bersih), None
        elif hasil.status_code == 503:
            time.sleep(3) # Tunggu 3 detik jika server penuh
        else:
            return None, f"Error {hasil.status_code}: {hasil.text}"
            
    return None, "Server Google sedang penuh. Silakan coba lagi nanti."

# --- 3. ANTARMUKA WEB STREAMLIT ---
st.set_page_config(page_title="AI BizFlow", page_icon="⚙️", layout="centered")

st.title("⚙️ AI BizFlow")
st.subheader("Ubah Ide Bisnis (BMC) Menjadi Alur BPMN 2.0 Otomatis")
st.write("Solusi AI cerdas untuk mempercepat pemetaan SOP dan arsitektur *enterprise* yang selaras dengan SDG 8 & SDG 9.")

# Input API Key (Bisa disembunyikan agar aman saat presentasi)
api_key = st.text_input("Masukkan Google Gemini API Key:", type="password")

# Input Ide Bisnis
ide_bisnis = st.text_area("Deskripsikan Ide Bisnismu atau Komponen Canvas di sini:", height=150, 
                          placeholder="Contoh: Klien memesan katering via aplikasi. Admin menerima pesanan lalu mengecek stok...")

if st.button("Generate File BPMN", type="primary"):
    if not api_key:
        st.warning("⚠️ Harap masukkan API Key terlebih dahulu.")
    elif not ide_bisnis:
        st.warning("⚠️ Harap isi deskripsi ide bisnis.")
    else:
        with st.spinner("Memproses dengan AI... Mohon tunggu sebentar."):
            hasil_json, pesan_error = ekstrak_ide_ke_json(api_key, ide_bisnis)
            
            if pesan_error:
                st.error(f"Gagal: {pesan_error}")
            elif hasil_json:
                st.success("✅ Ekstraksi berhasil! Mengonversi ke format XML Visual Paradigm...")
                
                # Konversi JSON ke XML String
                bpmn_xml_data = generate_bpmn_xml_string(hasil_json)
                
                # Tampilkan struktur JSON untuk demonstrasi ke juri
                with st.expander("Lihat Hasil Ekstraksi JSON (Klik untuk membuka)"):
                    st.json(hasil_json)
                
                # Tombol Download File
                st.download_button(
                    label="⬇️ Unduh File .bpmn",
                    data=bpmn_xml_data,
                    file_name="alur_sistem_otomatis.bpmn",
                    mime="application/xml"
                )
