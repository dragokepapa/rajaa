import random
from config import Config
from database import db

ROLES = ["Raja", "Mantri", "Chor", "Sipahi"]

class Game:
    def __init__(self):
        self.players = []
        self.usernames = {}
        self.roles = {}
        self.mantri = None
        self.chor = None
        self.current_round = 1
        self.max_rounds = Config.MAX_ROUNDS
        self.points = {}          # Round points

    def add_player(self, user_id, username):
        if user_id not in self.players:
            self.players.append(user_id)
            self.usernames[user_id] = username
            self.points[user_id] = 0

    def is_full(self):
        return len(self.players) >= Config.MAX_PLAYERS

    def assign_roles(self):
        roles = ROLES.copy()
        random.shuffle(roles)
        self.roles = dict(zip(self.players, roles))
        for uid, role in self.roles.items():
            if role == "Mantri": self.mantri = uid
            elif role == "Chor": self.chor = uid

    def check_guess(self, guessed_id):
        return guessed_id == self.chor

    def get_role_text(self, user_id):
        role = self.roles.get(user_id, "Unknown")
        return f"🎭 Tumhara role: **{role}**"

    def update_points(self, is_correct):
        for uid in self.players:
            role = self.roles[uid]
            if (is_correct and role == "Mantri") or (not is_correct and role == "Chor"):
                self.points[uid] += 30
            else:
                self.points[uid] += 10

    def get_final_ranking(self):
        ranked = sorted(self.points.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def give_end_game_rewards(self):
        ranking = self.get_final_ranking()
        rewards = [100, 50, 0, -50]
        for i, (user_id, _) in enumerate(ranking):
            if i < len(rewards):
                db.add_coins(user_id, rewards[i])