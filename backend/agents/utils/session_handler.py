from collections import deque
import os
import pickle


class SessionHandler:
    def __init__(self, session_id):
        dir_path = "backend/sessions"
        os.makedirs(dir_path, exist_ok=True)
        self.file_path = os.path.join(dir_path, f'{session_id}.pkl')
        
    def save(self, request, response="", max_items=1):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'rb') as file:
                queue = pickle.load(file)
        else:
            queue = deque(maxlen=max_items)

        queue.append((request, response))
        with open(self.file_path, 'wb') as file:
            pickle.dump(queue, file)

    def load(self):
        session_list = []
        if os.path.exists(self.file_path):
            with open(self.file_path, 'rb') as file:
                session = pickle.load(file)
            session_list = [{'request': item[0], 'response': item[1]} for item in session]
            return session_list