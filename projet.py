import threading
import time
import cv2
import numpy as np
import subprocess
import tkinter as tk
from PIL import Image, ImageTk
import os
import platform

# Configuration optimisée pour la vitesse
class Config:
    def __init__(self):
        self.settings = {
            "max_fps": 30,           # Augmenté à 30 FPS
            "max_size": 800,         # Résolution plus grande mais optimisée
            "window_width": 1024,
            "window_height": 576,
            "screenshot_path": "./screenshots",
            "quality": 80            # Qualité réduite pour la vitesse
        }

class AndroidDevice:
    def __init__(self, serial):
        self.serial = serial
        self.width, self.height = 1080, 1920  # Résolution standard

class ScreenRecorder:
    def __init__(self, device, config):
        self.device = device
        self.config = config
        self.running = False
        self.current_frame = None
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        self._frame_lock = threading.Lock()
        
    def start_recording(self):
        try:
            self.running = True
            # Utiliser plusieurs threads pour la capture
            self.capture_thread = threading.Thread(target=self._capture_loop)
            self.capture_thread.daemon = True
            self.capture_thread.start()
            
            # Thread séparé pour le calcul FPS
            self.fps_thread = threading.Thread(target=self._fps_loop)
            self.fps_thread.daemon = True
            self.fps_thread.start()
            
            return True
        except Exception as e:
            print(f"Erreur démarrage: {e}")
            return False
    
    def _fps_loop(self):
        """Calcul du FPS en temps réel"""
        last_count = 0
        while self.running:
            time.sleep(1.0)
            current_count = self.frame_count
            self.fps = current_count - last_count
            last_count = current_count
    
    def _capture_loop(self):
        """Boucle de capture ultra-rapide"""
        frame_time_target = 1.0 / self.config.settings["max_fps"]
        
        while self.running:
            try:
                start_time = time.time()
                
                success = self._capture_frame_optimized()
                if success:
                    self.frame_count += 1
                
                # Timing précis pour maintenir le FPS
                elapsed = time.time() - start_time
                sleep_time = max(0.001, frame_time_target - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                print(f"Erreur capture: {e}")
                time.sleep(0.05)
    
    def _capture_frame_optimized(self):
        """Méthode de capture optimisée pour la vitesse"""
        try:
            # Utilisation de screencap sans -p (plus rapide)
            result = subprocess.run(
                ['adb', '-s', self.device.serial, 'exec-out', 'screencap'],
                timeout=3,
                capture_output=True
            )
            
            if result.returncode == 0 and len(result.stdout) > 1000:
                # Traitement direct du buffer pour plus de vitesse
                nparr = np.frombuffer(result.stdout, np.uint8)
                
                # Décodage rapide
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Conversion BGR to RGB (plus rapide que cvtColor)
                    frame = frame[:, :, ::-1]  # Méthode numpy ultra-rapide
                    
                    # Redimensionnement conditionnel
                    height, width = frame.shape[:2]
                    max_size = self.config.settings["max_size"]
                    if width > max_size or height > max_size:
                        scale = min(max_size / width, max_size / height)
                        new_width = int(width * scale)
                        new_height = int(height * scale)
                        frame = cv2.resize(frame, (new_width, new_height), 
                                         interpolation=cv2.INTER_LINEAR)
                    
                    with self._frame_lock:
                        self.current_frame = frame
                    
                    return True
                    
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            pass
        
        return False

    def stop(self):
        self.running = False

class TouchController:
    def __init__(self, device):
        self.device = device
        self.running = True
        
    def send_touch(self, x, y):
        try:
            abs_x = int(x * self.device.width / 1000)
            abs_y = int(y * self.device.height / 1000)
            
            # Commande non-bloquante pour plus de réactivité
            subprocess.Popen(
                ['adb', '-s', self.device.serial, 'shell', 'input', 'tap', str(abs_x), str(abs_y)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            return False

    def stop(self):
        self.running = False

class DeviceManager:
    def __init__(self):
        self.devices = []
        self.current_device = None
        
    def discover_devices(self):
        self.devices = []
        try:
            # Redémarrage ADB pour plus de fiabilité
            try:
                subprocess.run(['adb', 'kill-server'], capture_output=True, timeout=3)
                time.sleep(1)
                subprocess.run(['adb', 'start-server'], capture_output=True, timeout=5)
                time.sleep(1)
            except:
                pass
            
            result = subprocess.run(
                ['adb', 'devices'],
                capture_output=True,
                text=True,
                timeout=8
            )
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if '\tdevice' in line:
                        serial = line.split('\t')[0]
                        self.devices.append(serial)
                        print(f"📱 Appareil trouvé: {serial}")
            
            return self.devices
        except Exception as e:
            print(f"Erreur découverte: {e}")
            return []
    
    def connect_device(self, serial):
        try:
            # Test de connexion rapide
            result = subprocess.run(
                ['adb', '-s', serial, 'shell', 'getprop', 'ro.product.model'],
                timeout=3,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                model = result.stdout.strip() or "Inconnu"
                self.current_device = AndroidDevice(serial)
                print(f"✅ Connecté à: {serial} ({model})")
                return True
        except Exception as e:
            print(f"Erreur connexion: {e}")
        return False

class ScrcpyApp:
    def __init__(self):
        self.config = Config()
        self.device_manager = DeviceManager()
        self.device = None
        self.screen_recorder = None
        self.touch_controller = None
        self.last_frame_time = time.time()
    
    def initialize(self):
        print("⚡ Initialisation ultra-rapide...")
        
        # Vérifier ADB rapidement
        try:
            subprocess.run(['adb', '--version'], capture_output=True, timeout=2)
        except:
            print("❌ ADB non trouvé")
            return False
        
        # Trouver les appareils
        devices = self.device_manager.discover_devices()
        if not devices:
            print("❌ Aucun appareil trouvé")
            return False
        
        # Se connecter
        if not self.device_manager.connect_device(devices[0]):
            print("❌ Échec connexion")
            return False
        
        self.device = self.device_manager.current_device
        
        # Initialiser les composants
        self.touch_controller = TouchController(self.device)
        self.screen_recorder = ScreenRecorder(self.device, self.config)
        
        print("✅ Initialisation réussie")
        return True

    def start(self):
        if not self.screen_recorder.start_recording():
            return False
        
        # Créer l'interface
        self.root = tk.Tk()
        self.setup_gui()
        self.update_frame()
        self.root.mainloop()
        return True

    def setup_gui(self):
        self.root.title("Scrcpy Ultra-Rapide ⚡")
        self.root.geometry(f"{self.config.settings['window_width']}x{self.config.settings['window_height']}")
        self.root.configure(bg='#2c3e50')
        
        # Frame principal
        main_frame = tk.Frame(self.root, bg='#2c3e50')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        # Canvas pour l'affichage
        self.canvas = tk.Canvas(main_frame, bg='#34495e', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Barre d'information
        info_frame = tk.Frame(main_frame, bg='#34495e', height=30)
        info_frame.pack(fill=tk.X, pady=(0, 2))
        info_frame.pack_propagate(False)
        
        self.info_label = tk.Label(info_frame, text="⚡ En attente...", 
                                  font=("Arial", 10), fg='#ecf0f1', bg='#34495e')
        self.info_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_touch)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Button-3>", self.on_back)
        
        self.root.bind("<Escape>", lambda e: self.stop())
        self.root.bind("<F1>", lambda e: self.screenshot())
        self.root.bind("<F2>", lambda e: self.toggle_stats())
        
        self.photo = None
        self.show_stats = True

    def toggle_stats(self):
        self.show_stats = not self.show_stats

    def on_touch(self, event):
        self.send_touch(event.x, event.y)

    def on_drag(self, event):
        self.send_touch(event.x, event.y)

    def on_release(self, event):
        self.send_touch(event.x, event.y)

    def on_back(self, event):
        try:
            subprocess.Popen(
                ['adb', '-s', self.device.serial, 'shell', 'input', 'keyevent', '4'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            pass

    def send_touch(self, x, y):
        if self.touch_controller:
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width > 0 and canvas_height > 0:
                rel_x = min(max(x / canvas_width * 1000, 0), 1000)
                rel_y = min(max(y / canvas_height * 1000, 0), 1000)
                self.touch_controller.send_touch(rel_x, rel_y)

    def screenshot(self):
        if self.screen_recorder and self.screen_recorder.current_frame is not None:
            try:
                os.makedirs(self.config.settings["screenshot_path"], exist_ok=True)
                timestamp = str(int(time.time() * 1000))
                filename = f"{self.config.settings['screenshot_path']}/screen_{timestamp}.jpg"
                
                frame = self.screen_recorder.current_frame
                Image.fromarray(frame).save(filename, "JPEG", 
                                          quality=self.config.settings["quality"],
                                          optimize=True)
                self.info_label.config(text=f"📸 {os.path.basename(filename)}")
            except Exception as e:
                self.info_label.config(text=f"❌ Erreur screenshot")

    def update_frame(self):
        """Boucle de rafraîchissement optimisée"""
        start_time = time.time()
        
        # Affichage de la frame
        if (self.screen_recorder and 
            self.screen_recorder.current_frame is not None):
            
            try:
                with self.screen_recorder._frame_lock:
                    frame = self.screen_recorder.current_frame
                
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()
                
                if canvas_width > 0 and canvas_height > 0:
                    # Redimensionnement rapide
                    pil_img = Image.fromarray(frame)
                    if pil_img.size != (canvas_width, canvas_height):
                        pil_img = pil_img.resize(
                            (canvas_width, canvas_height),
                            Image.Resampling.LANCZOS
                        )
                    
                    self.photo = ImageTk.PhotoImage(image=pil_img)
                    self.canvas.delete("all")
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                    
                    # Mettre à jour les infos de performance
                    if self.show_stats:
                        current_time = time.time()
                        frame_time = (current_time - self.last_frame_time) * 1000
                        self.last_frame_time = current_time
                        
                        info_text = (f"⚡ FPS: {self.screen_recorder.fps} | "
                                   f"⏱️  {frame_time:.1f}ms | "
                                   f"📊 {self.screen_recorder.frame_count}")
                        self.info_label.config(text=info_text)
                        
            except Exception as e:
                pass
        
        # Timing précis pour le rafraîchissement
        elapsed = (time.time() - start_time) * 1000
        target_delay = max(1, int(1000 / self.config.settings["max_fps"] - elapsed))
        self.root.after(target_delay, self.update_frame)

    def stop(self):
        if self.screen_recorder:
            self.screen_recorder.stop()
        if self.touch_controller:
            self.touch_controller.stop()
        self.root.quit()

def main():
    print("=" * 60)
    print("Scrcpy Ultra-Rapide ⚡ - Version Optimisée")
    print("=" * 60)
    
    # Nettoyer l'écran
    if platform.system() == "Windows":
        os.system('cls')
    else:
        os.system('clear')
    
    app = ScrcpyApp()
    
    if app.initialize():
        print("✅ Prêt à démarrer")
        print("📱 Appareil connecté")
        print("⚡ Lancement version ultra-rapide...")
        print("\n🎮 Contrôles:")
        print("• Clic gauche: Touch")
        print("• Clic droit: Back")
        print("• F1: Screenshot")
        print("• F2: Masquer/afficher les stats")
        print("• Échap: Quitter")
        
        try:
            app.start()
            print("✅ Fermeture normale")
        except Exception as e:
            print(f"❌ Erreur execution: {e}")
    else:
        print("❌ Échec initialisation")
        print("\n🔧 Solutions:")
        print("1. Vérifiez la connexion USB")
        print("2. Activez le débogage USB")
        print("3. Autorisez la connexion USB")
        print("4. Redémarrez ADB: adb kill-server && adb start-server")

if __name__ == "__main__":
    main()