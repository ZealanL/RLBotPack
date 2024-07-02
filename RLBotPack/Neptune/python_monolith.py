import time
import socket
import struct
import locker
import ctypes
from threading import Thread
from ctypes import *

import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

import collision_mesh_downloader

UDP_IP = "127.0.0.1"
UDP_SEND_PORT = 3938
UDP_RECEIVE_PORT = 3937

try:
	import torch
	from torch import nn
	torch.set_num_threads(1)
except ImportError:
	print("ERROR: Failed to import torch! Please install torch with pip.")
	time.sleep(100000)

##########################################
# Abridged version of: https://github.com/AechPro/rlgym-ppo/blob/main/rlgym_ppo/ppo/discrete_policy.py
"""
File: discrete_policy.py
Author: Matthew Allen

Description:
    An implementation of a feed-forward neural network which parametrizes a discrete distribution over a space of actions.
"""

class DiscreteFF(nn.Module):
    def __init__(self, input_shape, n_actions, layer_sizes, device):
        super().__init__()
        self.device = device

        assert len(layer_sizes) != 0, "AT LEAST ONE LAYER MUST BE SPECIFIED TO BUILD THE NEURAL NETWORK!"
        layers = [nn.Linear(input_shape, layer_sizes[0]), nn.ReLU()]
        prev_size = layer_sizes[0]
        for size in layer_sizes[1:]:
            layers.append(nn.Linear(prev_size, size))
            layers.append(nn.ReLU())
            prev_size = size

        layers.append(nn.Linear(layer_sizes[-1], n_actions))
        layers.append(nn.Softmax(dim=-1))
        self.model = nn.Sequential(*layers).to(self.device)

        self.n_actions = n_actions
		
    def get_output(self, obs):
        t = type(obs)
        if t != torch.Tensor:
            if t != np.array:
                obs = np.asarray(obs)
            obs = torch.as_tensor(obs, dtype=torch.float32, device=self.device)

        return self.model(obs)
		
##########################################

exe_thread = None
def start_bot_exe():
	global exe_thread
	print("Starting bot exe...")
	
	if not os.path.exists("./collision_meshes"):
			print("Collision meshes missing, calling downloader...")
			collision_mesh_downloader.run()
	
	dir_path = os.path.dirname(os.path.realpath(__file__))
	lib = cdll.LoadLibrary(os.path.join(dir_path, "NeptuneRLGymCPP.dll"))
	exe_thread = Thread(target=getattr(lib, "?main_run@@YAHXZ"))
	exe_thread.start()

start_bot_exe()

##########################################

@torch.no_grad()
def run_inference_sockets():
	global avg_infer_time
	global total_infers
		
	print("Creating sockets...")
	sock_out = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_in = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock_in.bind((UDP_IP, UDP_RECEIVE_PORT))

	print("Creating policy...")
	policy = DiscreteFF((420), 350, [2048, 1024, 1024, 1024], "cpu")

	print("Loading policy...")
	policy.load_state_dict(torch.load("PPO_POLICY.pt", map_location=torch.device("cpu")))

	print("Ready!")

	while True:
		data_in, addr = sock_in.recvfrom(1024 * 16)
		
		idx = struct.unpack("i", data_in[:4])[0]
		obs = struct.unpack_from("<{}f".format(len(data_in)//4 - 1), data_in[4:])

		start_time = time.time()
		with torch.no_grad():
			t_obs = torch.tensor(obs, requires_grad=False)
			action = policy.get_output(t_obs).argmax().item()
		
		data_out = struct.pack("ii", idx, action)
		sock_out.sendto(data_out, (UDP_IP, UDP_SEND_PORT))
		
####################################################

def run():
	try:
		with locker.Locker():
			start_bot_exe()
			run_inference_sockets()
	except OSError:
		pass # Just means the lock is doing its job and we blocked a second run