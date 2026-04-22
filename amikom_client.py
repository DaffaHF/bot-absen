"""
Client untuk berinteraksi dengan Student Portal Amikom Purwokerto.
Menangani login, mengambil data presensi, dan submit validasi kehadiran.
"""

import re
import requests
from bs4 import BeautifulSoup
from config import (
    BASE_URL,
    DEFAULT_KESESUAIAN_PERKULIAHAN,
    DEFAULT_KESESUAIAN_MATERI,
    DEFAULT_PENILAIAN_MHS,
    DEFAULT_KRITIK_SARAN,
)


class AmikomClient:
    """Client untuk mengakses Student Portal Amikom Purwokerto."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Referer": BASE_URL,
        })
        self.logged_in = False
        self.nim = None

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------

    def login(self, nim: str, password: str) -> bool:
        """Login ke portal. Return True jika berhasil."""
        url = BASE_URL + "auth/toenter"
        data = {"pengguna": nim, "passw": password}
        try:
            res = self.session.post(url, data=data, timeout=15)
            if res.text.strip() == "111":
                self.logged_in = True
                self.nim = nim
                return True
            return False
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # DATA FETCHERS
    # ------------------------------------------------------------------

    def get_student_info(self) -> dict:
        """Mengambil data profil mahasiswa dan list mata kuliah."""
        url = BASE_URL + "pembelajaran/presensimahasiswa"
        res = self.session.get(url, timeout=10)
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Ambil Nama
        nama = ""
        p_name = soup.find('p', class_='show_pengguna_on_desktop')
        if p_name:
            nama = p_name.get_text(strip=True).replace('/', '').strip()
            
        # Ambil Semester & Tahun Akademik
        selected_thn = soup.find("option", {"id": "thn_akademik", "selected": True})
        selected_sem = soup.find("option", {"id": "semester", "selected": True})
        thn_akademik = selected_thn.get_text(strip=True) if selected_thn else "Unknown"
        semester = selected_sem.get_text(strip=True) if selected_sem else "Unknown"
        
        # Ambil List Mata Kuliah
        matkul_list = []
        select_makul = soup.find("select", id="makul")
        if select_makul:
            for option in select_makul.find_all("option"):
                val = option.get("value")
                if val and val.strip():
                    text = option.get_text(strip=True)
                    # Hapus prefix id mk dari teks (contoh: "18693 - Analisis...")
                    if "-" in text:
                        text = text.split("-", 1)[1].strip()
                    matkul_list.append(text)
                    
        return {
            "nama": nama,
            "thn_akademik": thn_akademik,
            "semester": semester,
            "matkul": matkul_list
        }

    def get_makul_belum_validasi(self) -> list[dict]:
        """
        Ambil daftar mata kuliah yang punya presensi belum divalidasi.
        Return: [{"count": int, "makul": str}, ...]
        """
        url = BASE_URL + "pembelajaran/list_makul_belum_validasi"
        try:
            res = self.session.post(url, timeout=15)
            data = res.json()
            result = []
            for key in data:
                result.append({
                    "count": data[key]["count"],
                    "makul": data[key]["makul"],
                })
            return result
        except Exception:
            return []

    def get_semester_list(self, thn_akademik: str) -> list[dict]:
        """Ambil daftar semester untuk tahun akademik tertentu."""
        url = BASE_URL + "pembelajaran/getSem"
        res = self.session.post(url, data={"thn_akademik": thn_akademik}, timeout=15)
        soup = BeautifulSoup(res.text, "html.parser")
        options = soup.find_all("option")
        return [
            {"value": opt.get("value", ""), "text": opt.text.strip()}
            for opt in options
            if opt.get("value")
        ]

    def get_makul_list(self, thn_akademik: str, semester: str) -> list[dict]:
        """
        Ambil daftar mata kuliah.
        Return: [{"value": "kode_makul", "text": "Nama MK"}, ...]
        """
        url = BASE_URL + "pembelajaran/getmakul"
        data = {"thn_akademik": thn_akademik, "semester": semester}
        try:
            res = self.session.post(url, data=data, timeout=15)
            soup = BeautifulSoup(res.text, "html.parser")
            options = soup.find_all("option")
            return [
                {"value": opt.get("value", ""), "text": opt.text.strip()}
                for opt in options
                if opt.get("value")
            ]
        except Exception:
            return []

    def get_absensi_mhs(
        self, thn_akademik: str, semester: str, makul: str
    ) -> dict:
        """
        Ambil data absensi mahasiswa untuk satu mata kuliah.
        Return dict berisi info mata kuliah dan list presensi yang belum validasi.
        """
        url = BASE_URL + "pembelajaran/getabsenmhs"
        data = {
            "thn_akademik": thn_akademik,
            "semester": semester,
            "makul": makul,
        }
        try:
            res = self.session.post(url, data=data, timeout=15)
            return self._parse_absensi_html(res.text)
        except Exception:
            return {"nama_mk": "", "dosen": "", "belum_validasi": []}

    def _parse_absensi_html(self, html: str) -> dict:
        """
        Parse HTML response dari getabsenmhs.
        Cari tombol onclick="edit_presensikehadiran(...)" untuk presensi
        yang belum divalidasi (status B).
        """
        result = {
            "nama_mk": "",
            "dosen": "",
            "belum_validasi": [],
            "total_hadir": 0,
            "total_belum": 0,
        }

        soup = BeautifulSoup(html, "html.parser")

        # Cari panggilan fungsi edit_presensikehadiran di onclick
        # Pattern: edit_presensikehadiran(id,'mkl','teori','praktek','jenispilih')
        # Note: ID bisa berupa integer tanpa quote atau string dengan quote
        pattern = re.compile(
            r"edit_presensikehadiran\(\s*'?([^',\)]+)'?\s*,\s*'([^']*)'\s*,"
            r"\s*'([^']*)'\s*,\s*'([^']*)'\s*,\s*'([^']*)'\s*\)"
        )

        for element in soup.find_all(attrs={"onclick": True}):
            onclick = element.get("onclick", "")
            match = pattern.search(onclick)
            if match:
                result["belum_validasi"].append({
                    "id": match.group(1),
                    "mkl": match.group(2),
                    "teori": match.group(3),
                    "praktek": match.group(4),
                    "jenispilih": match.group(5),
                })

        # Juga coba parse via inline script jika onclick tidak ditemukan langsung
        if not result["belum_validasi"]:
            for match in pattern.finditer(html):
                result["belum_validasi"].append({
                    "id": match.group(1),
                    "mkl": match.group(2),
                    "teori": match.group(3),
                    "praktek": match.group(4),
                    "jenispilih": match.group(5),
                })

        result["total_belum"] = len(result["belum_validasi"])
        return result

    def get_presensi_detail(self, presensi_id: str) -> dict | None:
        """
        Ambil detail satu presensi untuk mengisi form validasi.
        GET /pembelajaran/ajax_editpresensi/{id}
        """
        url = BASE_URL + f"pembelajaran/ajax_editpresensi/{presensi_id}"
        try:
            res = self.session.get(url, timeout=15)
            return res.json()
        except Exception:
            return None

    # ------------------------------------------------------------------
    # SUBMIT VALIDASI
    # ------------------------------------------------------------------

    def submit_validasi(
        self,
        presensi_info: dict,
        detail: dict,
    ) -> bool:
        """
        Submit validasi presensi ke server.

        Args:
            presensi_info: dict dari _parse_absensi_html["belum_validasi"][i]
                          berisi id, mkl, teori, praktek, jenispilih
            detail: dict dari get_presensi_detail()
                   berisi id_presensi_mhs, id_presensi_dosen, asdoss, kriterias

        Return True jika berhasil.
        """
        url = BASE_URL + "pembelajaran/update_presensimhs"

        form_data = {
            "jenispilih": presensi_info["jenispilih"],
            "idpresensimhstexs": detail["id_presensi_mhs"],
            "idpresensidosen": detail["id_presensi_dosen"],
            "kuliahteori": presensi_info["teori"],
            "kuliahpraktek": presensi_info["praktek"],
            "kesesuaian_perkuliahan": DEFAULT_KESESUAIAN_PERKULIAHAN,
            "kesesuaian_materi": DEFAULT_KESESUAIAN_MATERI,
            "penilaianmhs": DEFAULT_PENILAIAN_MHS,
            "kritiksaran": DEFAULT_KRITIK_SARAN,
        }

        # Handle asisten dosen jika ada
        if detail.get("asdoss") and len(detail["asdoss"]) > 0:
            for idx, asdos in enumerate(detail["asdoss"]):
                form_data[f"asdos_npms[]"] = asdos.get("npm", "")
                # Isi semua kriteria asdos dengan nilai tertinggi
                if detail.get("kriterias"):
                    for krit in detail["kriterias"]:
                        krit_id = krit.get("asdos_krit_id", "")
                        # Ambil nilai tertinggi (biasanya index pertama atau terakhir)
                        if krit.get("nilai") and len(krit["nilai"]) > 0:
                            best_val = krit["nilai"][0].get("asdos_krit_nilai_id", "")
                            form_data[f"asdospenilaian_{idx}_{krit_id}"] = best_val

        try:
            res = self.session.post(url, data=form_data, timeout=15)
            result = res.json()
            return result.get("status", False)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # HIGH-LEVEL: VALIDASI SEMUA
    # ------------------------------------------------------------------

    def validasi_semua(self, thn_akademik: str = "2025/2026", semester: str = "2") -> dict:
        """
        Validasi semua presensi yang belum divalidasi.
        Return: {"sukses": int, "gagal": int, "detail": [str]}
        """
        result = {"sukses": 0, "gagal": 0, "detail": []}

        # Ambil daftar mata kuliah
        makul_list = self.get_makul_list(thn_akademik, semester)
        if not makul_list:
            result["detail"].append("❌ Tidak ada mata kuliah ditemukan.")
            return result

        for mk in makul_list:
            absensi = self.get_absensi_mhs(thn_akademik, semester, mk["value"])
            belum = absensi.get("belum_validasi", [])

            if not belum:
                continue

            for item in belum:
                detail = self.get_presensi_detail(item["id"])
                if not detail:
                    result["gagal"] += 1
                    result["detail"].append(
                        f"❌ {mk['text']} — gagal ambil detail presensi ID {item['id']}"
                    )
                    continue

                success = self.submit_validasi(item, detail)
                if success:
                    result["sukses"] += 1
                    tanggal = detail.get("tanggal", "?")
                    result["detail"].append(
                        f"✅ {mk['text']} — {tanggal}"
                    )
                else:
                    result["gagal"] += 1
                    result["detail"].append(
                        f"❌ {mk['text']} — gagal submit validasi"
                    )

        return result
