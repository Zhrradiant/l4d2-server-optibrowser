import socket
import struct
import ttkbootstrap as ttk

def create_outline_button(parent, text="", command=None, **kwargs):
    """创建带outline样式的按钮"""
    # 设置默认 padding，但如果 kwargs 中已经指定了 padding，则使用传入的值
    # if 'padding' not in kwargs:
    #     kwargs['padding'] = (18, 5)  # 默认 padding (水平, 垂直)
    return ttk.Button(
        parent,
        text=text,
        command=command,
        bootstyle="outline",
        **kwargs  # 传递所有额外参数
    )

def fetch_ips(region=0xFF):
    master_server = ('hl2master.steampowered.com', 27011)
    start_ip = b'0.0.0.0:0\x00'
    filters = b'\\appid\\550\x00'
    region_byte = struct.pack('B', region)
    packet = b'\x31' + region_byte + start_ip + filters

    servers = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)

    try:
        while True:
            sock.sendto(packet, master_server)
            data, _ = sock.recvfrom(4096)

            if not data.startswith(b'\xff\xff\xff\xff\x66\x0a'):
                continue

            data = data[6:]
            while len(data) >= 6:
                ip = struct.unpack('!BBBB', data[:4])
                port = struct.unpack('!H', data[4:6])[0]
                data = data[6:]

                if ip == (0, 0, 0, 0) and port == 0:
                    return servers

                ip_str = '.'.join(map(str, ip))
                servers.append(f"{ip_str}:{port}")
                next_ip = f"{ip_str}:{port}\x00".encode()
                packet = b'\x31' + region_byte + next_ip + filters

    except socket.timeout:
        return servers
    finally:
        sock.close()