from copy import deepcopy
from typing import Union

import gym
import numpy as np

from tools.env_config_formatter import convert_str_attr_to_float_env_config

import time


class LunarLanderAgent:
    """
	Class LunarLanderAgent. Vous devez modifier cette classe pour que votre agent puisse apprendre à jouer à LunarLander.

	Attributes:
		env_config (dict): Dictionnaire contenant les paramètres de l'environnement.
		observation_as_rgb (bool): True si l'environnement est configuré pour retourner des observations sous forme
			d'images.
	"""

    def __init__(self, env_config: dict, **kwargs):
        """
		Constructor de la classe LunarLanderAgent.

		:param env_config: Dictionnaire contenant les paramètres de l'environnement.
		:type env_config: dict
		:param kwargs: Arguments optionnels.
		"""
        self.env_config = env_config
        self.set_default_env_config()
        self.observation_as_rgb = self.env_config.get("render_mode", None) == "rgb_array"
        # self.time0 = time.time()
        self.observation_prev = np.zeros(8)
        self.countobs = 0

        self.params = [59.44565422926854, -12.944531289628515, -35.49561212000705, 2.779539138292493]
        self.new_params = [0,0,0,0]
        self.score = -100
        self.optimizing = False

    def PD(self, observation, mode):
        # check si les pattes sont au sol
        if (observation[6] or observation[7]) and mode == "continuous":
            return ([0, 0])
        elif observation[6] or observation[7]:
            return 0
        else:

            # gains
            if self.optimizing:
                Kp_pos = self.new_params[0]  # gain proportionnel de position
                Kd_pos = self.new_params[1]  # gain différentiel de position
                Kp_ang = self.new_params[2]  # gain proportionnel d'angle
                Kd_ang = self.new_params[3]  # gain différentiel d'angle
            else:
                Kp_pos = self.params[0]  # gain proportionnel de position
                Kd_pos = self.params[1]  # gain différentiel de position
                Kp_ang = self.params[2]  # gain proportionnel d'angle
                Kd_ang = self.params[3]  # gain différentiel d'angle
            # observables pertinents
            pos_horizontale = observation[0]
            vit_verticale = observation[3]
            vit_horizontale = observation[2]
            alt = observation[1]
            ang = observation[4]
            vit_ang = observation[5]
            # cibles
            pos_cible = np.abs(pos_horizontale)  # on veut que le lander vise un cone au dessus de la zone d'atterissage
            ang_cible = np.pi / 4 * (
                        pos_horizontale + vit_horizontale)  # on un angle pour propulser vers le centre pas plus grand que \pm 45 deg en fonction de la position et de la vitesse
            # erreurs
            pos_error = pos_cible - alt
            ang_error = ang_cible - ang

            # Commandes
            c_pos = Kp_pos * pos_error + Kd_pos * vit_horizontale  # gains proportionnels fois erreurs + gains diff fois vitesses (valeur différentielle); pas d'intégrateur
            c_ang = Kp_ang * ang_error + Kd_ang * vit_ang

            if mode == "continuous":
                action_space = np.clip([c_pos, c_ang], -1, 1)  # définition de l'action à prendre en mode continuous
            else:
                if max(np.abs(c_pos), np.abs(c_ang)) == np.abs(
                        c_pos):  # défintion de l'action à prendre en mode discret, on donne priorité à la commande la plus importante
                    action_space = 2
                elif c_ang < 0:
                    action_space = 1
                else:
                    action_space = 2
            #if (alt < -1.5 and vit_verticale < -1) or vit_verticale < -2:
                #action_space[0] = 1
            return action_space

    def set_default_env_config(self):
        self.env_config.setdefault('render_mode', None)
        self.env_config.setdefault('id', "LunarLander-v2")

    def make_env(self, env_config: dict = None):
        """
		Cette classe est utilisée pour créer un environnement avec les paramètres de self.env_config.
		Note: L'agent n'interagie pas avec cet environnement. Celui-ci est seulement utilisé pour récupérer des
			informations sur l'environnement comme l'espace d'actions et l'espace d'observations. Il peut aussi être
			utilisé pour tester l'agent.
		:return: Un environnement avec les paramètres de self.env_config.
		:rtype: gym.Env
		"""
        if env_config is None:
            env_config = self.env_config
        env_config = convert_str_attr_to_float_env_config(env_config)
        env = gym.make(**env_config)
        return env

    def get_action(self, observation: np.ndarray) -> Union[int, np.ndarray]:
        """
		Cette méthode est utilisée pour récupérer une action à partir d'une observation.

		:param observation: Observation de l'environnement.
		:type observation: np.ndarray
		:return: Action à effectuer dans l'environnement.
		:rtype: Union[int, np.ndarray]
		"""
        # time1 = time.time()
        # print(time1-self.time0)
        # self.time0 = time1
        env = self.make_env()
        action = env.action_space.sample()
        if observation != []:
            if self.countobs == 0:
                self.countobs = 1
                self.observation_prev = observation
            # print(observation)
            action = self.PD(observation, "continuous")
            self.observation_prev = observation
        env.close()
        return action

    def visualise_trajectory(self, seed=None, plot = False) -> float:
        """
		Cette méthode est utilisée pour visualiser une trajectoire de l'agent.
		:param seed: Seed pour l'environnement.
		:return: Cumulative reward de la trajectoire.
		"""
        viz_env_config = deepcopy(self.env_config)
        if plot == True:
            viz_env_config["render_mode"] = "human"
        else:
            viz_env_config["render_mode"] = "rbg_array"
        env = self.make_env(viz_env_config)
        observation, info = env.reset(seed=seed)
        terminal = False
        cumulative_rewards = 0.0
        while not terminal:
            if self.observation_as_rgb:
                rgb_observation = env.render()
                action = self.get_action(rgb_observation)
            else:
                action = self.get_action(observation)
            observation, reward, done, truncated, info = env.step(action)
            cumulative_rewards += reward
            terminal = done or truncated
        return cumulative_rewards


    def optimize(self, step):
        """
        optimisation des paramètres du PD par essais aléatoires
        """
        self.optimizing = True
        self.new_params[0] = self.params[0] + np.random.normal(0, 20.0 / np.sqrt(step))  # changement des paramètres selon du bruit de plus en plus petit avec le step qui augmente
        self.new_params[1] = self.params[1] + np.random.normal(0, 20.0 / np.sqrt(step))
        self.new_params[2] = self.params[2] + np.random.normal(0, 20.0 / np.sqrt(step))
        self.new_params[3] = self.params[3] + np.random.normal(0, 20.0 / np.sqrt(step))
        # 5 tests avec les nouveaux paramètres du PD
        test_scores = []
        for i in range(5): # on fait 5 tests avec les nouveaux paramètres
            #if step %25==0 and i==0: #le premier test tous les 25 sets de paramètres est affiché
            #    test_scores.append(self.visualise_trajectory(plot = True))
            #else:
            test_scores.append(self.visualise_trajectory())
        tests_avg = np.mean(test_scores)

        # on change les paramètres s'ils sont meilleurs
        if tests_avg > self.score:
            self.params = self.new_params
            self.score = tests_avg
        self.optimizing = False

if __name__ == '__main__':
    import json
    import time

    time0 = time.time_ns()
    configs = json.load(open(f"./env_configs.json", "r"))
    echelon_id: int = 0
    echelon_key = [key for key in configs.keys() if key.startswith(f"Echelon {echelon_id}")][0]
    agent = LunarLanderAgent(configs[echelon_key])
    agent.get_action([])
    #for i in range(1, 2001):            #
        #agent.optimize(i)               #
        #if i%25 == 0:                   # comment out ces lignes pour un test sans optimisation
            #print(agent.score)          #
            #print(agent.params)         #
    #print(agent.params)                 #
    cr = agent.visualise_trajectory(plot = True)
    print(f"Cumulative reward: {cr:.2f}")