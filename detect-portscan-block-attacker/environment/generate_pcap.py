#!/usr/bin/env python3
"""
Generate a pcap file with simulated network traffic including a port scan attack.
Uses raw struct packing to create a valid pcap file without external dependencies.
"""

import struct
import random
import socket

# Pcap global header
PCAP_MAGIC = 0xa1b2c3d4
PCAP_VERSION_MAJOR = 2
PCAP_VERSION_MINOR = 4
PCAP_THISZONE = 0
PCAP_SIGFIGS = 0
PCAP_SNAPLEN = 65535
PCAP_NETWORK = 1  # LINKTYPE_ETHERNET

# Target host IP
TARGET_IP = "192.168.1.100"
# Attacker IP
ATTACKER_IP = "10.45.33.187"
# Normal source IPs
NORMAL_IPS = [
    "192.168.1.10",
    "192.168.1.20",
    "192.168.1.30",
    "172.16.0.5",
    "172.16.0.12",
    "10.0.0.50",
    "10.0.0.77",
]
# Common ports for normal traffic
NORMAL_PORTS = [22, 80, 443, 8080, 53, 25, 110, 143, 993, 3306]

random.seed(42)

def ip_to_bytes(ip_str):
    return socket.inet_aton(ip_str)

def build_pcap_global_header():
    return struct.pack('<IHHiIII',
        PCAP_MAGIC, PCAP_VERSION_MAJOR, PCAP_VERSION_MINOR,
        PCAP_THISZONE, PCAP_SIGFIGS, PCAP_SNAPLEN, PCAP_NETWORK)

def build_ethernet_header(src_mac=None, dst_mac=None):
    if dst_mac is None:
        dst_mac = b'\x00\x1a\x2b\x3c\x4d\x5e'
    if src_mac is None:
        src_mac = b'\x00\x5e\x4d\x3c\x2b\x1a'
    ethertype = 0x0800  # IPv4
    return dst_mac + src_mac + struct.pack('!H', ethertype)

def build_ip_header(src_ip, dst_ip, payload_len):
    version_ihl = 0x45
    dscp_ecn = 0
    total_length = 20 + payload_len  # IP header + payload
    identification = random.randint(0, 65535)
    flags_fragment = 0x4000  # Don't fragment
    ttl = 64
    protocol = 6  # TCP
    checksum = 0  # Simplified
    src = ip_to_bytes(src_ip)
    dst = ip_to_bytes(dst_ip)
    header = struct.pack('!BBHHHBBH4s4s',
        version_ihl, dscp_ecn, total_length, identification,
        flags_fragment, ttl, protocol, checksum, src, dst)
    return header

def build_tcp_header(src_port, dst_port, flags=0x02):
    seq = random.randint(0, 0xFFFFFFFF)
    ack = 0
    data_offset = 0x50  # 5 words, no options
    window = 65535
    checksum = 0
    urgent = 0
    header = struct.pack('!HHIIBBHHH',
        src_port, dst_port, seq, ack,
        data_offset, flags, window, checksum, urgent)
    return header

def build_packet(src_ip, dst_ip, src_port, dst_port, tcp_flags=0x02):
    eth = build_ethernet_header()
    tcp = build_tcp_header(src_port, dst_port, tcp_flags)
    ip = build_ip_header(src_ip, dst_ip, len(tcp))
    return eth + ip + tcp

def build_pcap_record(packet_data, ts_sec, ts_usec):
    incl_len = len(packet_data)
    orig_len = len(packet_data)
    header = struct.pack('<IIII', ts_sec, ts_usec, incl_len, orig_len)
    return header + packet_data

def main():
    packets = []
    base_ts = 1700000000

    # Generate normal traffic: each normal IP connects to a few ports (2-5)
    for ip in NORMAL_IPS:
        num_connections = random.randint(2, 5)
        ports_used = random.sample(NORMAL_PORTS, min(num_connections, len(NORMAL_PORTS)))
        for port in ports_used:
            src_port = random.randint(1024, 65535)
            ts = base_ts + random.randint(0, 300)
            ts_usec = random.randint(0, 999999)
            # SYN packet
            pkt = build_packet(ip, TARGET_IP, src_port, port, tcp_flags=0x02)
            packets.append((ts, ts_usec, pkt))
            # SYN-ACK response
            pkt2 = build_packet(TARGET_IP, ip, port, src_port, tcp_flags=0x12)
            packets.append((ts, ts_usec + 1000, pkt2))
            # ACK
            pkt3 = build_packet(ip, TARGET_IP, src_port, port, tcp_flags=0x10)
            packets.append((ts, ts_usec + 2000, pkt3))

    # Generate port scan from attacker: 80 distinct destination ports
    scan_ports = random.sample(range(1, 1024), 80)
    for port in scan_ports:
        src_port = random.randint(1024, 65535)
        ts = base_ts + random.randint(5, 30)
        ts_usec = random.randint(0, 999999)
        # SYN packet (port scan)
        pkt = build_packet(ATTACKER_IP, TARGET_IP, src_port, port, tcp_flags=0x02)
        packets.append((ts, ts_usec, pkt))
        # Some ports respond with RST (closed)
        if random.random() < 0.7:
            pkt2 = build_packet(TARGET_IP, ATTACKER_IP, port, src_port, tcp_flags=0x14)
            packets.append((ts, ts_usec + 500, pkt2))

    # Sort packets by timestamp
    packets.sort(key=lambda x: (x[0], x[1]))

    # Write pcap file
    with open('traffic.pcap', 'wb') as f:
        f.write(build_pcap_global_header())
        for ts_sec, ts_usec, pkt_data in packets:
            f.write(build_pcap_record(pkt_data, ts_sec, ts_usec))

    # Print stats for verification
    total = len(packets)
    attacker_pkts = sum(1 for _, _, p in packets
        if p[26:30] == ip_to_bytes(ATTACKER_IP) or p[30:34] == ip_to_bytes(ATTACKER_IP))
    # Count only packets FROM attacker
    attacker_from = sum(1 for _, _, p in packets if p[26:30] == ip_to_bytes(ATTACKER_IP))
    print(f"Total packets: {total}")
    print(f"Attacker packets (from attacker): {attacker_from}")
    print(f"Attacker packets (involving attacker): {attacker_pkts}")
    print(f"Unique ports scanned: {len(scan_ports)}")
    print(f"Attacker IP: {ATTACKER_IP}")

if __name__ == '__main__':
    main()
