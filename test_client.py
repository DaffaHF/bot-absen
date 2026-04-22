"""Quick test script to verify the AmikomClient works correctly."""
from amikom_client import AmikomClient

def test():
    client = AmikomClient()
    
    # Test 1: Login
    print("=== Test Login ===")
    ok = client.login("24SA31A022", "96376")
    print(f"Login: {'OK' if ok else 'FAILED'}")
    if not ok:
        return
    
    # Test 2: Cek belum validasi
    print("\n=== Test Belum Validasi ===")
    belum = client.get_makul_belum_validasi()
    print(f"Belum validasi: {belum}")
    
    # Test 3: Get makul list
    print("\n=== Test Get Makul ===")
    makul_list = client.get_makul_list("2025/2026", "2")
    for mk in makul_list:
        print(f"  - {mk['value']}: {mk['text']}")
    
    # Test 4: Get absensi untuk setiap makul
    print("\n=== Test Get Absensi ===")
    for mk in makul_list:
        absensi = client.get_absensi_mhs("2025/2026", "2", mk["value"])
        belum_list = absensi.get("belum_validasi", [])
        if belum_list:
            print(f"\n  {mk['text']}:")
            for item in belum_list:
                print(f"    - ID: {item['id']}, jenispilih: {item['jenispilih']}")
                
                # Test 5: Get detail
                detail = client.get_presensi_detail(item["id"])
                if detail:
                    print(f"      id_presensi_mhs: {detail.get('id_presensi_mhs')}")
                    print(f"      id_presensi_dosen: {detail.get('id_presensi_dosen')}")
                    print(f"      tanggal: {detail.get('tanggal')}")
                    print(f"      judul_materi: {detail.get('judul_materi')}")
                    print(f"      asdoss: {len(detail.get('asdoss', []))} asisten")
                else:
                    print(f"      FAILED to get detail")

if __name__ == "__main__":
    test()
