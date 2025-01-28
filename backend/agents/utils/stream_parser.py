
class Stream_Parser:
    def __init__(self, json_string):
        self.json_string = json_string

    def parser(self):
        objects_start_end_indices = []
        brace_count = 0
        start_index = None

        # Iterate over the string to find all JSON objects
        for i, char in enumerate(self.json_string):
            if char == '{':
                if brace_count == 0:
                    start_index = i  # Potential start of a JSON object
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_index is not None:
                    # End of a JSON object, save its start and end indices
                    objects_start_end_indices.append((start_index, i))
                    start_index = None

        # If we have found at least two JSON objects, return the one before last
        if len(objects_start_end_indices) >= 2:
            start, end = objects_start_end_indices[-2]  # Second to last object indices
            return self.json_string[start:end+1]

        # If there are not enough JSON objects
        return None