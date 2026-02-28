package com.battlepass.plugin.data;

import com.battlepass.plugin.BattlePassPlugin;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

public final class PlayerDataStore {

    private final BattlePassPlugin plugin;
    private final File playerDir;
    private final Map<UUID, PlayerData> cache = new HashMap<>();

    public PlayerDataStore(BattlePassPlugin plugin) {
        this.plugin = plugin;
        this.playerDir = new File(plugin.getDataFolder(), "players");
        if (!playerDir.exists() && !playerDir.mkdirs()) {
            plugin.getLogger().warning("Could not create players data directory.");
        }
    }

    public PlayerData get(UUID uuid) {
        return cache.computeIfAbsent(uuid, this::load);
    }

    public void unload(UUID uuid) {
        PlayerData data = cache.remove(uuid);
        if (data != null) {
            save(data);
        }
    }

    public void saveAll() {
        for (PlayerData data : cache.values()) {
            save(data);
        }
    }

    private PlayerData load(UUID uuid) {
        File file = new File(playerDir, uuid + ".yml");
        PlayerData data = new PlayerData(uuid);
        if (!file.exists()) {
            return data;
        }

        YamlConfiguration config = YamlConfiguration.loadConfiguration(file);
        data.setXp(config.getLong("xp", 0));
        data.setPremiumOwned(config.getBoolean("premium-owned", false));

        for (String raw : config.getStringList("claimed-free")) {
            try {
                data.getClaimedFree().add(Integer.parseInt(raw));
            } catch (NumberFormatException ignored) {
            }
        }

        for (String raw : config.getStringList("claimed-premium")) {
            try {
                data.getClaimedPremium().add(Integer.parseInt(raw));
            } catch (NumberFormatException ignored) {
            }
        }
        return data;
    }

    public void save(PlayerData data) {
        File file = new File(playerDir, data.getUuid() + ".yml");
        YamlConfiguration config = new YamlConfiguration();
        config.set("xp", data.getXp());
        config.set("premium-owned", data.isPremiumOwned());
        config.set("claimed-free", data.getClaimedFree().stream().map(String::valueOf).toList());
        config.set("claimed-premium", data.getClaimedPremium().stream().map(String::valueOf).toList());

        try {
            config.save(file);
        } catch (IOException exception) {
            plugin.getLogger().warning("Failed to save player data for " + data.getUuid() + ": " + exception.getMessage());
        }
    }
}
