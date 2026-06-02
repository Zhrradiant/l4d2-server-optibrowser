import threading
import time
from threading import Thread
from collections import deque
import random
import a2s

from language_strings import load_language_from_config, get_string
load_language_from_config()

class AsyncServerQuery:
    def __init__(self, callback, mode=get_string("stable", "稳定"), app=None):
        self.callback = callback
        self.running = True
        self.blocked_ips = set()
        self.mode = mode
        self._update_intervals()
        self.main_last_time = time.perf_counter()
        self.total_tasks = 0
        self.completed_tasks = 0
        self.main_queue = deque()
        self.main_lock = threading.Lock()
        self.main_last_time = time.perf_counter()
        self.pending_servers = deque()
        self.add_task_lock = threading.Lock()
        self.app = app
        Thread(target=self._task_adder, daemon=True).start()
        Thread(target=self._main_scheduler, daemon=True).start()

    def _update_intervals(self):
        if self.mode == get_string("aggressive", "暴力"):
            self.main_interval = 0.002
            self.adder_interval = 0.002
        elif self.mode == get_string("fast", "快速"):
            self.main_interval = 0.003
            self.adder_interval = 0.003
        elif self.mode == get_string("standard", "标准"):
            self.main_interval = 0.01
            self.adder_interval = 0.01
        else:
            self.main_interval = 0.2
            self.adder_interval = 0.2

    def _main_scheduler(self):
        import ctypes
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(1)

        try:
            while self.running:
                now = time.perf_counter()
                if now - self.main_last_time >= self.main_interval:
                    addr = None
                    with self.main_lock:
                        if self.main_queue:
                            addr = self.main_queue.popleft()
                            self.main_last_time = now
                    if addr:
                        Thread(target=self._process_main_task, args=(addr,), daemon=True).start()
                time.sleep(0.001)
        finally:
            winmm.timeEndPeriod(1)

    def _process_main_task(self, addr):
        try:
            self.callback(('start_query', {'addr': addr}))
            start_time = time.perf_counter()
            result = self._query_server(addr)
            latency = int((time.perf_counter() - start_time) * 1000)
            if result:
                result[1]['latency'] = latency
                self.callback(result)
        except Exception as e:
            print(f"Main task error: {e}")
        finally:
            self.completed_tasks += 1

    def get_progress(self):
        return self.completed_tasks, self.total_tasks

    def _query_server(self, addr):
        try:
            ip, port = addr.split(":")
            info = a2s.info((ip, int(port)), timeout=2)

            # 先立即返回服务器基本信息
            result = ('success', {
                'addr': addr,
                'vac': "[V]" if info.vac_enabled else "",
                'name': info.server_name,
                'game': info.game,
                'map': info.map_name,
                'players': info.player_count,
                'max_players': info.max_players,
                'keywords': getattr(info, 'keywords', '无'),
                'players_data': []  # 先返回空数组，后续异步填充
            })

            # 异步获取玩家信息（不阻塞主查询）
            if self.app and getattr(self.app, 'player_info_enabled', False):
                # 获取当前页面名称
                current_page = self.app.current_page if hasattr(self.app, 'current_page') else 'main'
                Thread(target=self._query_players_async, args=(addr, ip, port, current_page), daemon=True).start()

            return result

        except Exception as e:
            return ('error', {'addr': addr, 'msg': str(e)})

    def _query_players_async(self, addr, ip, port, page_name):
        """异步查询玩家信息，关联到特定页面"""
        try:
            players = a2s.players((ip, int(port)), timeout=2)
            # 获取服务器信息以获取服务器名称
            try:
                info = a2s.info((ip, int(port)), timeout=2)
                server_name = info.server_name
            except:
                server_name = "未知服务器"

            # 通过 app 更新玩家信息窗口，关联到当前页面
            if self.app and hasattr(self.app, 'player_info_window'):
                self.app.player_info_window.add_player_info(addr, server_name, players, page_name)
        except:
            # 玩家信息查询失败，静默处理
            pass

    def _task_adder(self):
        while self.running:
            if self.pending_servers:
                with self.main_lock:
                    addr = self.pending_servers.popleft()
                    self.main_queue.append(addr)
            time.sleep(self.adder_interval)

    def add_task(self, servers):
        with self.add_task_lock:
            self.blocked_ips = self.app.load_blocked_ips()
            existing = set(self.pending_servers) | set(self.main_queue)
            unique_servers = list(dict.fromkeys(servers))

            # 过滤被屏蔽的服务器
            new_servers = []
            for s in unique_servers:
                if s in existing:
                    continue

                ip, port = s.split(':')
                is_blocked = False

                # 检查是否被全IP屏蔽
                if ip in self.blocked_ips['full_ips']:
                    is_blocked = True

                # 检查是否被单端口屏蔽
                elif s in self.blocked_ips['single_ports']:
                    is_blocked = True

                # 检查是否匹配自定义规则
                else:
                    for custom_ip, rule in self.blocked_ips['custom_rules']:
                        if ip == custom_ip:
                            if '-' in rule:
                                # 处理端口范围
                                try:
                                    start_port, end_port = rule.split('-')
                                    start = int(start_port)
                                    end = int(end_port)
                                    port_num = int(port)
                                    if start <= port_num <= end:
                                        is_blocked = True
                                        break
                                except ValueError:
                                    # 如果转换失败，跳过此规则
                                    pass
                            else:
                                # 单个端口
                                try:
                                    if int(port) == int(rule):
                                        is_blocked = True
                                        break
                                except ValueError:
                                    # 如果转换失败，跳过此规则
                                    pass

                if not is_blocked:
                    new_servers.append(s)

            random.shuffle(new_servers)
            self.pending_servers.extend(new_servers)
            self.total_tasks += len(new_servers)
            return len(new_servers)

    def stop(self):
        self.running = False
        with self.main_lock:
            self.main_queue.clear()