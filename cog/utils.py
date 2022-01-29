from datetime import datetime, timedelta
class cooldown:
    def __init__(self):
        self.on_cooldown = {}
    
    def _create_token_(self, id, cmd_name):
        return f"{id}/{cmd_name}"
    
    def add_cooldown(self, id, cmd_name):
        """ Add a <guild_id/<cmd_name> token to the dict """
        self.on_cooldown[self._create_token_(id, cmd_name)] = datetime.utcnow()

    def is_on_cooldown(self, id, cmd_name, cooldownSeconds) -> bool:
        """check if a token is still on cooldown"""
        
        currentTime = datetime.utcnow()
        token=self._create_token_(id, cmd_name)
        
        # Check all cooldown dict
        for key in list(self.on_cooldown.keys()):
            if self.on_cooldown[key] + timedelta(seconds=cooldownSeconds) < currentTime:
                # cooldown expired
                del self.on_cooldown[key]
        
        if token in self.on_cooldown.keys():
            if self.on_cooldown[token] + timedelta(seconds=cooldownSeconds) > currentTime:
                # command still on cooldown
                retry_after = (currentTime-self.on_cooldown[token]).seconds
                return True
            else:
                return False
        else:
            return False
