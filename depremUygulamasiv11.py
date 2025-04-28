import sys
import requests
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QTableWidget, 
                            QTableWidgetItem, QComboBox, QHeaderView, QLineEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QIcon, QColor
import winsound  
import psutil as psu
import os
import webbrowser  
import math

class EarthquakeTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.api_url = "https://api.orhanaydogdu.com.tr/deprem/kandilli/live" #Deprem Verilerini Çektiğimiz API
        self.last_earthquake_time = None  # Son depremin zamanını takip etmek için
        self.initUI()
        
        # Her 3 dakikada bir güncelle
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_earthquakes)
        self.update_timer.start(180000)  # 3 dakika
        
    def initUI(self):
        self.setWindowTitle('Türkiye Deprem Takip')
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1c1c1c;
                border-radius:8px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                border-radius:8px;
            }
            QPushButton {
                background-color: #ff0000;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #9c1c00;
                
            }
            QTableWidget {
                background-color:#1c1c1c;
                color: white;
                border:none;
                gridline-color:1px solid white;
                border-radius:6px;
                
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: white;
                padding: 5px;
                border: none;
            }
            QComboBox {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 8px;
            }
        """)

        # Ana widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Kontrol paneli
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)

        # Arama çubuğu
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Ara")
        self.search_box.textChanged.connect(self.filter_earthquakes)
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                padding: 8px;
                border-radius: 8px;
                min-width: 200px;
            }
        """)
        control_layout.addWidget(QLabel("Arama:"))
        control_layout.addWidget(self.search_box)

        # Filtre
        self.magnitude_filter = QComboBox()
        self.magnitude_filter.addItems(['Tümü','2.0+', '3.0+', '4.0+', '5.0+'])
        self.magnitude_filter.currentTextChanged.connect(self.filter_earthquakes)
        control_layout.addWidget(QLabel("Büyüklük Filtresi:"))
        control_layout.addWidget(self.magnitude_filter)

        # Yenile butonu
        refresh_btn = QPushButton("🔄 Yenile")
        refresh_btn.clicked.connect(self.update_earthquakes)
        control_layout.addWidget(refresh_btn)

        # Son güncelleme zamanı
        self.update_time_label = QLabel()
        control_layout.addWidget(self.update_time_label)

        control_layout.addStretch()
        layout.addWidget(control_panel)

        # Deprem tablosu
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            'Tarih/Saat', 'Büyüklük', 'Yer', 'Şiddet', 'Harita'
        ])
        
        # Tablo ayarları
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Yer sütunu esnek
        for i in range(6):  # Diğer sütunlar içeriğe göre
            if i != 5:
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # İlk verileri yükle
        self.update_earthquakes()

    def update_earthquakes(self):
        try:
            response = requests.get(self.api_url)
            data = response.json()
            
            if data['status']:
                earthquakes = data['result']
                
                # En son depremi kontrol et ve gerekirse uyarı ver
                if earthquakes:
                    latest_eq = earthquakes[0]  # En son deprem
                    latest_time = datetime.strptime(latest_eq['date'], '%Y.%m.%d %H:%M:%S')
                    
                    if (self.last_earthquake_time is None or 
                        latest_time > self.last_earthquake_time):
                        # Yeni bir deprem var
                        if float(latest_eq['mag']) >= 4.5:
                            try:
                                winsound.PlaySound("SystemExclamation", winsound.Beep)
                            except Exception as e:
                                print(f"Ses çalma hatası: {e}")
                    
                    self.last_earthquake_time = latest_time
                
                self.all_earthquakes = earthquakes  # Filtreleme için sakla
                self.display_earthquakes(earthquakes)
                
                self.update_time_label.setText(
                    f"Son Güncelleme: {datetime.now().strftime('%H:%M:%S')}"
                )
            else:
                raise Exception("Veri alınamadı")

        except Exception as e:
            self.update_time_label.setText(f"Hata: {str(e)}")

    def display_earthquakes(self, earthquakes):
        self.table.setRowCount(0)  # Tabloyu temizle
        
        magnitude_filter = self.magnitude_filter.currentText()
        min_magnitude = 0.0 if magnitude_filter == 'Tümü' else float(magnitude_filter[:-1])

        for eq in earthquakes:
            try:
                magnitude = float(eq['mag'])
                
                if magnitude >= min_magnitude:
                    row = self.table.rowCount()
                    self.table.insertRow(row)
                    
                    # Tarih/Saat - API'den gelen date formatını kullan
                    date_str = eq.get('date') or eq.get('datetime', 'Bilinmiyor')
                    try:
                        # Tarihi parse et ve formatla
                        date = datetime.strptime(date_str, '%Y.%m.%d %H:%M:%S')
                        date_formatted = date.strftime('%d.%m.%Y %H:%M')
                    except:
                        date_formatted = date_str
                    
                    self.table.setItem(row, 0, QTableWidgetItem(date_formatted))
                    
                    # Büyüklük ve renklendirme
                    magnitude_item = QTableWidgetItem(f"{magnitude:.1f}")
                    magnitude_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    
                    if magnitude >= 6.0:
                        magnitude_item.setBackground(QColor('red'))
                    elif magnitude >= 4.0 or magnitude>=5.9:
                        magnitude_item.setBackground(QColor('#e36e07'))
                    elif magnitude >= 3.0:
                        magnitude_item.setBackground(QColor('blue'))
                    else:
                        magnitude_item.setBackground(QColor("green"))
                    
                    self.table.setItem(row, 1, magnitude_item)
                    
                    # Diğer bilgiler - Koordinatları doğru şekilde al
                    try:
                        depth = float(eq.get('depth', 0))
                        lat = float(eq.get('lat', 0))
                        lng = float(eq.get('lng', 0))
                        
                        # Derinlik ve koordinat değerlerinin mantıklı aralıklarda olup olmadığını kontrol et
                        if (0 <= depth <= 700 and  # Derinlik kontrolü (0-700 km arası mantıklı)
                            35 <= lat <= 43 and    # Türkiye'nin enlem aralığı
                            25 <= lng <= 45):      # Türkiye'nin boylam aralığı
                            
                            # Derinliği en yakın 0.1'e yuvarla
                            depth = round(depth, 1)
                            # Koordinatları 4 ondalık basamağa yuvarla (yaklaşık 11 metre hassasiyet)
                            lat = round(lat, 4)
                            lng = round(lng, 4)
                            
                            self.table.setItem(row, 2, QTableWidgetItem(f"{depth:.1f} km"))
                            self.table.setItem(row, 3, QTableWidgetItem(f"{lat:.4f}°K"))  # Kuzey için K kullanıldı
                            self.table.setItem(row, 4, QTableWidgetItem(f"{lng:.4f}°D"))  # Doğu için D kullanıldı
                        else:
                            self.table.setItem(row, 2, QTableWidgetItem("Hatalı Veri"))
                            self.table.setItem(row, 3, QTableWidgetItem("Hatalı Veri"))
                            self.table.setItem(row, 4, QTableWidgetItem("Hatalı Veri"))
                    except (ValueError, TypeError):
                        self.table.setItem(row, 2, QTableWidgetItem("Hatalı Veri"))
                        self.table.setItem(row, 3, QTableWidgetItem("Hatalı Veri"))
                        self.table.setItem(row, 4, QTableWidgetItem("Hatalı Veri"))
                    
                    self.table.setItem(row, 5, QTableWidgetItem(eq.get('title', 'Bilinmiyor')))
                    
                    # Tahmini şiddet
                    intensity = self.estimate_intensity(magnitude, depth)
                    intensity_item = QTableWidgetItem(intensity)
                    intensity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.table.setItem(row, 6, intensity_item)
                    
                    # Harita butonu - Koordinatları kontrol et
                    map_btn = QPushButton("🗺️")
                    map_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #4CAF50;
                            color: white;
                            border: none;
                            padding: 5px;
                            border-radius: 8px;
                        }
                        QPushButton:hover {
                            background-color: #45a049;
                        }
                    """)
                    
                    try:
                        lat = float(eq.get('lat', 0))
                        lng = float(eq.get('lng', 0))
                        depth = float(eq.get('depth', 0))
                        
                        # Derinlik ve koordinat değerlerinin mantıklı aralıklarda olup olmadığını kontrol et
                        if (0 <= depth <= 700 and      # Derinlik kontrolü (0-700 km arası mantıklı)
                            35 <= lat <= 43 and        # Türkiye'nin enlem aralığı
                            25 <= lng <= 45):          # Türkiye'nin boylam aralığı
                            
                            # Koordinatları 4 ondalık basamağa yuvarla
                            lat = round(lat, 4)
                            lng = round(lng, 4)
                            map_btn.clicked.connect(lambda checked, lat=lat, lng=lng: self.open_in_maps(lat, lng))
                            map_btn.setToolTip(f"Haritada göster: {lat}°K, {lng}°D")
                        else:
                            map_btn.setEnabled(False)
                            map_btn.setText("❌")
                            if not (35 <= lat <= 43) or not (25 <= lng <= 45):
                                map_btn.setToolTip("Koordinatlar Türkiye sınırları dışında")
                            elif not (0 <= depth <= 700):
                                map_btn.setToolTip("Hatalı Veri")
                    except (ValueError, TypeError):
                        map_btn.setEnabled(False)
                        map_btn.setText("❌")
                        map_btn.setToolTip("Hatalı Veri")
                    
                    self.table.setCellWidget(row, 7, map_btn)
                    
            except Exception as e:
                print(f"Deprem verisi işlenirken hata: {e}")
                continue

    def filter_earthquakes(self):
        if hasattr(self, 'all_earthquakes'):
            filtered_earthquakes = self.all_earthquakes.copy()
            
            # Büyüklük filtresi
            magnitude_filter = self.magnitude_filter.currentText()
            if magnitude_filter != 'Tümü':
                min_magnitude = float(magnitude_filter.replace('+', ''))
                filtered_earthquakes = [eq for eq in filtered_earthquakes 
                                      if float(eq.get('mag', 0)) >= min_magnitude]
            
            # Arama filtresi
            search_text = self.search_box.text().lower().strip()
            if search_text:
                filtered_earthquakes = [eq for eq in filtered_earthquakes 
                                      if search_text in eq.get('title', '').lower()]
            
            self.display_earthquakes(filtered_earthquakes) #Depremleri Konuma Göre Filtrele

    def estimate_intensity(self, magnitude, depth):
        """Basit bir şiddet tahmini"""
        if magnitude >= 7.0:
            return "Yıkıcı"
        elif magnitude >= 6.0:
            return "Çok Şiddetli"
        elif magnitude >= 5.0:
            return "Şiddetli"
        elif magnitude >= 4.0:
            return "Orta"
        elif magnitude >= 3.0:
            return "Hafif"
        else:
            return "Çok Hafif"

    def open_in_maps(self, lat, lng):
        """Google Haritalar'da konumu aç"""
        # Google Maps'te daha detaylı görünüm için zoom seviyesi ekle
        url = f"https://www.google.com/maps?q={lat},{lng}&z=10"
        webbrowser.open(url)

def main():
    app = QApplication(sys.argv)
    window = EarthquakeTracker()
    window.show()
    pid = os.getpid()
    process=psu.Process(pid)
    bellek_kullanimi=process.memory_info().rss/(1024*1024)
    print(f"Bellek Kullanımı : {bellek_kullanimi:.2f} Mb ")
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
