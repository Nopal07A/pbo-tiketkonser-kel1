from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

# =====================================================================
# 1. ABSTRAKSI (ABSTRACTION)
# Penjelasan: Menyembunyikan detail implementasi yang rumit. 
# Class BaseModel ini tidak akan pernah dibuatkan tabel fisiknya di database 
# (karena abstract = True). Ia murni bertindak sebagai cetak biru (blueprint) 
# untuk menyeragamkan pembuatan field `id` berjenis UUID pada model-model lain,
# membebaskan developer dari keharusan memikirkan mekanisme primary key berulang kali.
# =====================================================================
class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


# =====================================================================
# 2. PEWARISAN (INHERITANCE)
# Penjelasan: Class anak mengambil atribut dan metode dari class induk.
# Class User mewarisi AbstractUser bawaan Django.
# Class Venue, Event, dll. mewarisi BaseModel, sehingga secara otomatis 
# memiliki field `id` tanpa perlu ditulis ulang. Ini memenuhi prinsip DRY (Don't Repeat Yourself).
# =====================================================================
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    no_hp = models.CharField(max_length=15, blank=True)
    is_organizer = models.BooleanField(default=False)


class Venue(BaseModel):
    nama = models.CharField(max_length=200)
    kota = models.CharField(max_length=100)

    # =====================================================================
    # 4. POLIMORFISME (POLYMORPHISM)
    # Penjelasan: Metode yang sama (__str__) memiliki perilaku spesifik 
    # tergantung pada objek tempat ia dipanggil. Di Venue, ia mencetak "Nama - Kota".
    # =====================================================================
    def __str__(self):
        return f"{self.nama} - {self.kota}"


class Event(BaseModel):
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE)
    nama_konser = models.CharField(max_length=200)
    artis = models.CharField(max_length=200)
    tanggal = models.DateTimeField()
    tipe = models.CharField(max_length=50) 
    poster = models.ImageField(upload_to='event_posters/', null=True, blank=True)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'is_organizer': True})

    # --- 4. POLIMORFISME ---
    # Di Event, pemanggilan __str__ yang sama akan menghasilkan string format berbeda: "Nama Konser oleh Artis".
    def __str__(self):
        return f"{self.nama_konser} oleh {self.artis}"


class TicketCategory(BaseModel):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    nama_kategori = models.CharField(max_length=100)
    harga = models.IntegerField()
    kuota = models.IntegerField()
    pakai_kursi = models.BooleanField(default=False)

    # =====================================================================
    # 3. ENKAPSULASI (ENCAPSULATION)
    # Penjelasan: Melindungi state objek dan menyembunyikan komputasi internal. 
    # UI/Views tidak perlu repot membandingkan angka kuota > 0 secara manual, 
    # cukup membaca properti is_available untuk mendapatkan status True/False.
    # =====================================================================
    @property
    def is_available(self):
        return self.kuota > 0

    def __str__(self):
        return f"{self.nama_kategori} ({self.event.nama_konser})"


class Seat(BaseModel):
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    kode_kursi = models.CharField(max_length=10)
    status = models.CharField(max_length=20, default='TERSEDIA')

    # --- 3. ENKAPSULASI ---
    @property
    def is_booked(self):
        return self.status != 'TERSEDIA'

    def __str__(self):
        return f"{self.kode_kursi} [{self.status}]"


class Order(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    waktu_pesan = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='PENDING')
    total_harga = models.IntegerField(default=0)

    def __str__(self):
        return f"Order: {self.id} | Pemesan: {self.user.username}"


class OrderItem(BaseModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    category = models.ForeignKey(TicketCategory, on_delete=models.CASCADE)
    seat = models.ForeignKey(Seat, on_delete=models.SET_NULL, null=True, blank=True)
    harga_satuan = models.IntegerField()

    def __str__(self):
        return f"Item {self.category.nama_kategori} (Order {self.order.id})"


class Payment(BaseModel):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    metode = models.CharField(max_length=50)
    status_bayar = models.CharField(max_length=20, default='UNPAID')
    kode_referensi = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Payment {self.id} - {self.status_bayar}"


class Ticket(BaseModel):
    order_item = models.OneToOneField(OrderItem, on_delete=models.CASCADE)
    kode_qr = models.CharField(max_length=255, unique=True)
    sudah_dipakai = models.BooleanField(default=False)

    # --- 3. ENKAPSULASI ---
    # Metode mark_as_used membungkus proses pengubahan state objek dari dalam.
    # Ini memastikan validasi (cek apakah tiket sudah dipakai) dilakukan di dalam class, 
    # mencegah data dimanipulasi secara asal dan membabi buta dari luar class.
    def mark_as_used(self):
        if not self.sudah_dipakai:
            self.sudah_dipakai = True
            self.save()

    def __str__(self):
        return f"Tiket {self.kode_qr[:8]}... | Status Dipakai: {self.sudah_dipakai}"


# ForumMessage dibiarkan terpisah dari BaseModel untuk mempertahankan perilaku Meta bawaan spesifiknya.
class ForumMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='forum_messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='forum_images/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username} di {self.event.nama_konser}"