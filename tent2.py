import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import os
import io
import base64
import requests
import tempfile
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches

class ImageLayoutApp:
    def __init__(self):
        self.image_paths = []
        self.preview_images = []
        self.image_files = []
        self.uploaded_images = []
        
        self.img_width = 8.0
        self.img_height = 8.0
        self.spacing = 1.0
        self.margin = 2.0
        self.paper_orientation = "แนวตั้ง"
        self.rotate_top = True
        self.auto_fit = False
        self.DPI = 300

    def cm_to_px(self, cm):
        return int(cm * self.DPI / 2.54)

    def get_github_files(self, repo_url, path=""):
        try:
            if "github.com" in repo_url:
                api_url = repo_url.replace("github.com", "api.github.com/repos")
                if not api_url.endswith("/contents"):
                    api_url = api_url.rstrip("/") + "/contents"
                if path:
                    api_url = api_url + "/" + path
            else:
                return []
            
            response = requests.get(api_url)
            if response.status_code == 200:
                files = response.json()
                image_files = []
                for file in files:
                    if file['type'] == 'file':
                        ext = os.path.splitext(file['name'])[1].lower()
                        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff']:
                            image_files.append({
                                'name': file['name'],
                                'download_url': file['download_url'],
                                'path': file['path']
                            })
                    elif file['type'] == 'dir':
                        sub_files = self.get_github_files(repo_url, file['path'])
                        image_files.extend(sub_files)
                return image_files
            else:
                st.error(f"ไม่สามารถเชื่อมต่อ GitHub: {response.status_code}")
                return []
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            return []

    def load_image_from_url(self, url):
        try:
            response = requests.get(url)
            if response.status_code == 200:
                img = Image.open(io.BytesIO(response.content))
                return img
            else:
                st.error(f"ไม่สามารถโหลดภาพ: {url}")
                return None
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")
            return None

    def process_uploaded_images(self, uploaded_files):
        self.uploaded_images = []
        for uploaded_file in uploaded_files:
            try:
                img = Image.open(uploaded_file)
                self.uploaded_images.append({
                    'name': uploaded_file.name,
                    'image': img,
                    'size': uploaded_file.size
                })
            except Exception as e:
                st.error(f"ไม่สามารถโหลดภาพ {uploaded_file.name}: {str(e)}")
        
        self.image_files = [{'name': img['name'], 'image': img['image']} for img in self.uploaded_images]
        return len(self.uploaded_images)

    def generate_preview(self):
        if not self.image_files:
            st.warning("กรุณาเลือกไฟล์ภาพ (อัปโหลดจากเครื่อง หรือจาก GitHub)")
            return
        try:
            self.preview_images.clear()
            img_width_cm = st.session_state.get('img_width', self.img_width)
            img_height_cm = st.session_state.get('img_height', self.img_height)
            spacing_cm = st.session_state.get('spacing', self.spacing)
            margin_cm = st.session_state.get('margin', self.margin)
            paper_orientation = st.session_state.get('paper_orientation', self.paper_orientation)
            rotate_top = st.session_state.get('rotate_top', self.rotate_top)
            auto_fit = st.session_state.get('auto_fit', self.auto_fit)
            
            if paper_orientation == "แนวตั้ง":
                paper_w_cm, paper_h_cm = 21.0, 29.7
            else:
                paper_w_cm, paper_h_cm = 29.7, 21.0
            
            paper_w = self.cm_to_px(paper_w_cm)
            paper_h = self.cm_to_px(paper_h_cm)
            margin = self.cm_to_px(margin_cm)
            
            progress_bar = st.progress(0)
            
            for idx, file_info in enumerate(self.image_files):
                if 'download_url' in file_info:
                    img = self.load_image_from_url(file_info['download_url'])
                else:
                    img = file_info['image']
                if img is None:
                    continue
                
                if auto_fit:
                    max_h = (paper_h - 2 * margin - self.cm_to_px(spacing_cm)) / 2
                    max_w = paper_w - 2 * margin
                    img_ratio = img.width / img.height
                    img_h = int(max_h)
                    img_w = int(max_h * img_ratio)
                    if img_w > max_w:
                        img_w = int(max_w)
                        img_h = int(max_w / img_ratio)
                else:
                    img_w = self.cm_to_px(img_width_cm)
                    img_h = self.cm_to_px(img_height_cm)
                
                total_height = 2 * img_h + self.cm_to_px(spacing_cm)
                if total_height > paper_h - 2 * margin:
                    st.warning(f"ภาพที่ {idx+1} ({file_info['name']}) ใหญ่เกินไป กรุณาลดขนาดหรือเปิด Auto Fit")
                    continue
                
                paper = Image.new('RGB', (paper_w, paper_h), 'white')
                img_resized = img.resize((img_w, img_h), Image.Resampling.LANCZOS)
                
                top_img = img_resized.copy()
                if rotate_top:
                    top_img = top_img.rotate(180)
                bottom_img = img_resized.copy()
                
                total_height = 2 * img_h + self.cm_to_px(spacing_cm)
                start_y = (paper_h - total_height) // 2
                start_x = (paper_w - img_w) // 2
                
                paper.paste(top_img, (start_x, start_y))
                bottom_y = start_y + img_h + self.cm_to_px(spacing_cm)
                paper.paste(bottom_img, (start_x, bottom_y))
                
                self.preview_images.append(paper)
                progress_bar.progress((idx + 1) / len(self.image_files))
            
            progress_bar.empty()
            if self.preview_images:
                st.success(f"✅ สร้างตัวอย่างสำเร็จ {len(self.preview_images)} แผ่น")
            else:
                st.warning("ไม่สามารถสร้างภาพได้ กรุณาตรวจสอบไฟล์ที่เลือก")
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาด: {str(e)}")

    def create_download_buttons(self):
        if not self.preview_images:
            return
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📥 ดาวน์โหลด PNG")
            for idx, img in enumerate(self.preview_images):
                img_bytes = io.BytesIO()
                img.save(img_bytes, format='PNG')
                img_bytes.seek(0)
                st.download_button(
                    label=f"แผ่นที่ {idx+1} (PNG)",
                    data=img_bytes,
                    file_name=f"page_{idx+1:03d}.png",
                    mime="image/png",
                    key=f"png_{idx}"
                )
        
        with col2:
            st.subheader("📄 ดาวน์โหลด PDF")
            try:
                import img2pdf
                image_bytes_list = []
                for img in self.preview_images:
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    image_bytes_list.append(img_bytes.getvalue())
                pdf_bytes = img2pdf.convert(image_bytes_list)
                st.download_button(
                    label="📄 ดาวน์โหลด PDF (หลายหน้า)",
                    data=pdf_bytes,
                    file_name="output.pdf",
                    mime="application/pdf",
                    key="pdf_download"
                )
            except ImportError:
                st.warning("กรุณาติดตั้ง img2pdf: pip install img2pdf")
        
        with col3:
            st.subheader("📊 ดาวน์โหลด PowerPoint")
            try:
                prs = Presentation()
                blank_slide_layout = prs.slide_layouts[6]
                for idx, img in enumerate(self.preview_images):
                    slide = prs.slides.add_slide(blank_slide_layout)
                    img_bytes = io.BytesIO()
                    img.save(img_bytes, format='PNG')
                    img_bytes.seek(0)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
                        tmp_img.write(img_bytes.read())
                        tmp_img_path = tmp_img.name
                    slide.shapes.add_picture(tmp_img_path, Inches(1), Inches(1), width=Inches(6), height=Inches(8))
                pptx_bytes = io.BytesIO()
                prs.save(pptx_bytes)
                pptx_bytes.seek(0)
                st.download_button(
                    label="📊 ดาวน์โหลด PowerPoint (PPTX)",
                    data=pptx_bytes,
                    file_name="output.pptx",
                    mime="