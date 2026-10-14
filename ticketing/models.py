from datetime import timedelta
import uuid
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ==============================================================================
# 1. ABSTRAKSI & INHERITANCE (Base Class)
# ==============================================================================
# [INHERITANCE]: Mewarisi fungsionalitas inti ORM dari models.Model bawaan Django.
# [ABSTRAKSI]: class Meta 'abstract = True' menjadikan class ini murni template.
# Django tidak akan membuatkan tabel database untuk BaseModel.
class BaseModel(models.Model):
    # Menyembunyikan kompleksitas pembuatan Primary Key berbasis UUID untuk semua kelas turunan.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


# ==============================================================================
# 2. INHERITANCE (Custom User)
# ==============================================================================
# [INHERITANCE]: Mewarisi seluruh logika autentikasi, hashing password, dan perizinan
# dari AbstractUser tanpa perlu menulis ulang sistem login dari nol.
# [ENKAPSULASI]: Mengelompokkan atribut autentikasi standar bersama field kustom (no_hp, is_organizer).
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_hp = models.CharField(max_length=15, blank=True)
    is_organizer = models.BooleanField(default=False)


# ==============================================================================
# 3. VENUE
# ==============================================================================
# [INHERITANCE]: Mewarisi field 'id' (UUID) dari BaseModel.
class Venue(BaseModel):
    nama = models.CharField(max_length=200)
    kota = models.CharField(max_length=100)

    # [POLIMORFISME]: Overriding method bawaan '__str__' dari object/models.Model.
    # Setiap model merespons pemanggilan str(obj) dengan representasi string spesifik dirinya.
    def __str__(self):
        return f"{self.nama} ({self.kota})"


# ==============================================================================
# 4. EVENT
# ==============================================================================
class Event(BaseModel):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    nama_konser = models.CharField(max_length=200)
    artis = models.CharField(max_length=200)
    tanggal = models.DateTimeField()
    tipe = models.CharField(max_length=50)
    poster = models.ImageField(upload_to="event_posters/", null=True, blank=True)
    # Konsistensi enkapsulasi relasi: merujuk ke AUTH_USER_MODEL
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"is_organizer": True},
    )

    # [ABSTRAKSI & ENKAPSULASI]: Logika penentuan status waktu disembunyikan di dalam model.
    # Caller dari luar cukup memanggil 'event.time_status' tanpa perlu tahu rumus timedelta
    # dan manipulasi objek datetime di baliknya.
    @property
    def time_status(self):
        sekarang = timezone.now()
        hari_h_awal = self.tanggal.replace(hour=0, minute=0, second=0, microsecond=0)
        hari_h_akhir = hari_h_awal + timedelta(days=1)

        if sekarang < hari_h_awal:
            return "UPCOMING"
        elif hari_h_awal <= sekarang < hari_h_akhir:
            return "LIVE"
        else:
            return "EXPIRED"

    # [ABSTRAKSI]: Mengabstraksi kalkulasi batas waktu 3 hari menjadi boolean sederhana.
    @property
    def is_forum_closed(self):
        batas_waktu = self.tanggal + timedelta(days=3)
        return timezone.now() >= batas_waktu

    # [ABSTRAKSI]: Mengisolasi komputasi selisih detik ke jam di dalam batas kelas.
    @property
    def jam_tersisa_forum(self):
        if self.is_forum_closed:
            return 0
        batas_waktu = self.tanggal + timedelta(days=3)
        selisih = batas_waktu - timezone.now()
        return int(selisih.total_seconds() // 3600)

    # [POLIMORFISME]: Overriding method __str__ khusus untuk entitas Event.
    def __str__(self):
        return f"{self.nama_konser} oleh {self.artis}"


# ==============================================================================
# 5. TICKET CATEGORY & SEAT
# ==============================================================================
class TicketCategory(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nama_kategori = models.CharField(max_length=100)
    harga = models.IntegerField()
    kuota = models.IntegerField()
    pakai_kursi = models.BooleanField(default=False)

    # [ENKAPSULASI]: Menyediakan read-only computed property untuk mengecek ketersediaan.
    # Mencegah logic pengecekan 'kuota > 0' bertebaran di file views/controller.
    @property
    def is_available(self):
        return self.kuota > 0

    # [POLIMORFISME]: Overriding __str__ untuk menampilkan relasi event dan kategori tiket.
    def __str__(self):
        return f"{self.nama_kategori} ({self.event.nama_konser})"


class Seat(BaseModel):
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    kode_kursi = models.CharField(max_length=10)
    status = models.CharField(max_length=20, default="TERSEDIA")

    # [ENKAPSULASI]: Menyembunyikan evaluasi kondisi status internal.
    @property
    def is_booked(self):
        return self.status != "TERSEDIA"

    # [POLIMORFISME]: Overriding __str__ menampilkan status kursi.
    def __str__(self):
        return f"{self.kode_kursi} [{self.status}]"


# ==============================================================================
# 6. ORDER & ORDER ITEM
# ==============================================================================
class Order(BaseModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    waktu_pesan = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="PENDING")
    total_harga = models.IntegerField(default=0)

    # [POLIMORFISME]: Overriding __str__ khusus format Order.
    def __str__(self):
        return f"Order: {self.id} | Pemesan: {self.user.username}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, blank=True)
    harga_satuan = models.IntegerField()

    # [POLIMORFISME]: Overriding __str__ khusus rincian item pesanan.
    def __str__(self):
        return f"Item {self.category.nama_kategori} (Order {self.order.id})"


# ==============================================================================
# 7. PAYMENT & TICKET
# ==============================================================================
class Payment(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    metode = models.CharField(max_length=50)
    status_bayar = models.CharField(max_length=20, default="UNPAID")
    kode_referensi = models.CharField(max_length=100, blank=True)

    # [POLIMORFISME]: Overriding __str__ khusus transaksi pembayaran.
    def __str__(self):
        return f"Payment {self.id} [{self.status_bayar}]"


class Ticket(BaseModel):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    kode_qr = models.CharField(max_length=255, unique=True)
    sudah_dipakai = models.BooleanField(default=False)

    # [ENKAPSULASI]: Mutasi state dibungkus di dalam method objek itu sendiri.
    # Dunia luar (view/service) dilarang mengubah 'ticket.sudah_dipakai = True' secara manual.
    # Method ini memvalidasi aturan bisnis: hanya tiket yang belum dipakai yang boleh diubah.
    def mark_as_used(self):
        if not self.sudah_dipakai:
            self.sudah_dipakai = True
            self.save()

    # [POLIMORFISME]: Overriding __str__ untuk identitas tiket terpotong.
    def __str__(self):
        return (
            f"Tiket {self.kode_qr[:8]}... | Status Dipakai: {self.sudah_dipakai}"
        )


# ==============================================================================
# 8. FORUM MESSAGE
# ==============================================================================
# [INHERITANCE]: Harus konsisten mewarisi BaseModel, bukan models.Model secara mentah,
# agar standarisasi primary key UUID tetap berlaku di seluruh domain sistem.
class ForumMessage(BaseModel):
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="forum_messages"
    )
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to="forum_images/", blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]

    # [POLIMORFISME]: Overriding __str__ untuk identitas pesan pengirim.
    def __str__(self):
        return f"{self.sender.username} di {self.event.nama_konser}"