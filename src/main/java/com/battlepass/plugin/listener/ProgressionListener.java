package com.battlepass.plugin.listener;

import com.battlepass.plugin.BattlePassPlugin;
import com.battlepass.plugin.config.ConfigManager;
import com.battlepass.plugin.service.BattlePassService;
import org.bukkit.GameMode;
import org.bukkit.Material;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.EntityType;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.entity.EntityDeathEvent;
import org.bukkit.scheduler.BukkitTask;

public final class ProgressionListener implements Listener {

    private final BattlePassPlugin plugin;
    private final ConfigManager configManager;
    private final BattlePassService battlePassService;
    private BukkitTask playtimeTask;

    public ProgressionListener(BattlePassPlugin plugin, ConfigManager configManager, BattlePassService battlePassService) {
        this.plugin = plugin;
        this.configManager = configManager;
        this.battlePassService = battlePassService;
    }

    public void reload() {
        if (playtimeTask != null) {
            playtimeTask.cancel();
            playtimeTask = null;
        }

        if (!configManager.getMainConfig().getBoolean("xp-sources.playtime.enabled", true)) {
            return;
        }

        int seconds = Math.max(10, configManager.getMainConfig().getInt("xp-sources.playtime.interval-seconds", 300));
        long amount = Math.max(1, configManager.getMainConfig().getLong("xp-sources.playtime.xp-per-interval", 50));

        playtimeTask = plugin.getServer().getScheduler().runTaskTimer(plugin, () -> {
            for (Player player : plugin.getServer().getOnlinePlayers()) {
                if (shouldIgnore(player)) {
                    continue;
                }
                battlePassService.addXp(player, amount, configManager.getMainConfig().getBoolean("xp-sources.playtime.notify-player", false));
            }
        }, seconds * 20L, seconds * 20L);
    }

    public void shutdown() {
        if (playtimeTask != null) {
            playtimeTask.cancel();
            playtimeTask = null;
        }
    }

    @EventHandler
    public void onEntityDeath(EntityDeathEvent event) {
        if (!configManager.getMainConfig().getBoolean("xp-sources.mob-kill.enabled", true)) {
            return;
        }

        Player killer = event.getEntity().getKiller();
        if (killer == null || shouldIgnore(killer)) {
            return;
        }

        ConfigurationSection section = configManager.getMainConfig().getConfigurationSection("xp-sources.mob-kill.values");
        if (section == null) {
            return;
        }

        EntityType type = event.getEntityType();
        long xp = section.getLong(type.name(), section.getLong("default", 0));
        if (xp <= 0) {
            return;
        }

        battlePassService.addXp(killer, xp, configManager.getMainConfig().getBoolean("xp-sources.mob-kill.notify-player", false));
    }

    @EventHandler
    public void onBlockBreak(BlockBreakEvent event) {
        if (!configManager.getMainConfig().getBoolean("xp-sources.block-break.enabled", false)) {
            return;
        }

        Player player = event.getPlayer();
        if (shouldIgnore(player)) {
            return;
        }

        ConfigurationSection section = configManager.getMainConfig().getConfigurationSection("xp-sources.block-break.values");
        if (section == null) {
            return;
        }

        Material material = event.getBlock().getType();
        long xp = section.getLong(material.name(), section.getLong("default", 0));
        if (xp <= 0) {
            return;
        }

        battlePassService.addXp(player, xp, configManager.getMainConfig().getBoolean("xp-sources.block-break.notify-player", false));
    }

    private boolean shouldIgnore(Player player) {
        boolean ignoreCreative = configManager.getMainConfig().getBoolean("xp-sources.ignore-creative", true);
        boolean ignoreSpectator = configManager.getMainConfig().getBoolean("xp-sources.ignore-spectator", true);

        return (ignoreCreative && player.getGameMode() == GameMode.CREATIVE)
                || (ignoreSpectator && player.getGameMode() == GameMode.SPECTATOR);
    }
}
