package com.battlepass.plugin.listener;

import com.battlepass.plugin.BattlePassPlugin;
import com.battlepass.plugin.data.PlayerDataStore;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.player.PlayerQuitEvent;

public final class PlayerConnectionListener implements Listener {

    private final PlayerDataStore dataStore;

    public PlayerConnectionListener(BattlePassPlugin plugin, PlayerDataStore dataStore) {
        this.dataStore = dataStore;

        plugin.getServer().getOnlinePlayers().forEach(player -> dataStore.get(player.getUniqueId()));
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent event) {
        dataStore.get(event.getPlayer().getUniqueId());
    }

    @EventHandler
    public void onQuit(PlayerQuitEvent event) {
        dataStore.unload(event.getPlayer().getUniqueId());
    }
}
