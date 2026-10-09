import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests
import threading
import time

class TempMailApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Công Cụ Tạo Email 10 Phút Pro")
        self.root.geometry("600x500")
        self.root.config(bg="#f0f2f5")

        self.base_url = "https://www.1secmail.com/api/v1/"
        self.login = ""
        self.domain = ""
        self.is_running = False

        # --- GIAO DIỆN (UI) ---
        
        # Tiêu đề
        title_label = tk.Label(root, text="HỆ THỐNG TẠO EMAIL TẠM THỜI", font=("Arial", 16, "bold"), bg="#f0f2f5", fg="#1877f2")
        title_label.pack(pady=10)

        # Khung hiển thị Email
        frame_email = tk.Frame(root, bg="#f0f2f5")
        frame_email.pack(pady=5)

        tk.Label(frame_email, text="Email của bạn:", font=("Arial", 11), bg="#f0f2f5").pack(side=tk.LEFT, padx=5)
        
        self.email_entry = tk.Entry(root, font=("Arial", 12), width=35, justify="center")
        self.email_entry.pack(pady=5)

        # Các nút chức năng
        frame_btn = tk.Frame(root, bg="#f0f2f5")
        frame_btn.pack(pady=10)

        self.btn_gen = tk.Button(frame_btn, text="Tạo Email Mới", font=("Arial", 10, "bold"), bg="#42b72a", fg="white", padx=10, pady=5, command=self.generate_new_email)
        self.btn_gen.pack(side=tk.LEFT, padx=5)

        self.btn_copy = tk.Button(frame_btn, text="Copy Email", font=("Arial", 10), bg="#1877f2", fg="white", padx=10, pady=5, command=self.copy_email)
        self.btn_copy.pack(side=tk.LEFT, padx=5)

        self.btn_refresh = tk.Button(frame_btn, text="Làm Mới Hộp Thư", font=("Arial", 10), bg="#ffa000", fg="white", padx=10, pady=5, command=self.check_inbox)
        self.btn_refresh.pack(side=tk.LEFT, padx=5)

        # Khung danh sách thư đến
        tk.Label(root, text="Hộp thư đến (Inbox):", font=("Arial", 11, "bold"), bg="#f0f2f5").pack(anchor="w", padx=30, pady=5)
        
        self.inbox_listbox = tk.Listbox(root, font=("Arial", 10), height=5)
        self.inbox_listbox.pack(fill=tk.X, padx=30, pady=5)
        self.inbox_listbox.bind('<<ListboxSelect>>', self.read_selected_email)

        # Khung đọc nội dung chi tiết
        tk.Label(root, text="Nội dung chi tiết thư:", font=("Arial", 11, "bold"), bg="#f0f2f5").pack(anchor="w", padx=30, pady=5)
        
        self.content_text = scrolledtext.ScrolledText(root, font=("Arial", 10), height=8, wrap=tk.WORD)
        self.content_text.pack(fill=tk.BOTH, padx=30, pady=5, expand=True)

        # Tạo sẵn email đầu tiên khi mở app
        self.generate_new_email()

    def generate_new_email(self):
        """Tạo địa chỉ email ngẫu nhiên từ API"""
        try:
            response = requests.get(f"{self.base_url}?action=genRandomMailbox&count=1")
            if response.status_code == 200:
                email = response.json()[0]
                self.login, self.domain = email.split('@')
                
                # Hiển thị lên ô nhập
                self.email_entry.delete(0, tk.END)
                self.email_entry.insert(0, email)
                
                # Reset hộp thư
                self.inbox_listbox.delete(0, tk.END)
                self.content_text.delete('1.0', tk.END)
                
                # Bắt đầu luồng tự động check thư ngầm
                self.start_auto_check()
            else:
                messagebox.showerror("Lỗi", "Không thể tạo email mới từ máy chủ!")
        except Exception as e:
            messagebox.showerror("Lỗi Kết Nối", str(e))

    def copy_email(self):
        """Sao chép email vào bộ nhớ tạm"""
        email = self.email_entry.get()
        if email:
            self.root.clipboard_clear()
            self.root.clipboard_append(email)
            messagebox.showinfo("Thành công", "Đã sao chép email vào Clipboard!")

    def check_inbox(self):
        """Kiểm tra danh sách tin nhắn mới"""
        if not self.login or not self.domain:
            return
        
        url = f"{self.base_url}?action=getMessages&login={self.login}&domain={self.domain}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                messages = response.json()
                self.inbox_listbox.delete(0, tk.END)
                
                # Lưu danh sách message ID để tra cứu
                self.current_messages = messages
                for msg in messages:
                    display_text = f"Từ: {msg['from']} | Tiêu đề: {msg['subject']}"
                    self.inbox_listbox.insert(tk.END, display_text)
        except Exception as e:
            print(f"Lỗi check inbox: {e}")

    def read_selected_email(self, event):
        """Đọc nội dung chi tiết khi người dùng click vào một thư trong danh sách"""
        selection = self.inbox_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        msg_id = self.current_messages[index]['id']

        url = f"{self.base_url}?action=readMessage&login={self.login}&domain={self.domain}&id={msg_id}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                detail = response.json()
                
                # Hiển thị nội dung ra ô text
                self.content_text.delete('1.0', tk.END)
                info = f"Người gửi: {detail.get('from')}\n" \
                       f"Chủ đề: {detail.get('subject')}\n" \
                       f"Thời gian: {detail.get('date')}\n" \
                       f"-"*50 + "\n\n" + \
                       detail.get('body', '')
                self.content_text.insert(tk.END, info)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc nội dung thư: {e}")

    def start_auto_check(self):
        """Chạy vòng lặp ngầm kiểm tra thư mới mỗi 6 giây mà không đơ giao diện"""
        self.is_running = True
        def background_worker():
            while self.is_running:
                self.check_inbox()
                time.sleep(6)
        
        # Dùng Thread để ứng dụng không bị đơ khi gọi mạng
        threading.Thread(target=background_worker, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = TempMailApp(root)
    root.mainloop()
