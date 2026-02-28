package com.battlepass.plugin.service;

import com.battlepass.plugin.BattlePassPlugin;
import com.battlepass.plugin.config.ConfigManager;
import com.battlepass.plugin.data.PlayerData;
import com.battlepass.plugin.data.PlayerDataStore;
import com.battlepass.plugin.model.RewardTrack;
import com.battlepass.plugin.model.Tier;
import com.battlepass.plugin.util.PlaceholderUtil;
import org.bukkit.Bukkit;
import org.bukkit.command.ConsoleCommandSender;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

public final class BattlePassService {

    private final BattlePassPlugin plugin;
    private final ConfigManager configManager;
    private final PlayerDataStore dataStore;
    private final MessageService messages;

    private final List<Tier> tiers = new ArrayList<>();

    public BattlePassService(BattlePassPlugin plugin, ConfigManager configManager, PlayerDataStore dataStore, MessageService messages) {
        this.plugin = plugin;
        this.configManager = configManager;
        this.dataStore = dataStore;
        this.messages = messages;
    }

    public void reload() {
        tiers.clear();

        ConfigurationSection root = configManager.getTiers().getConfigurationSection("tiers");
        if (root == null) {
            plugin.getLogger().warning("tiers.yml does not contain 'tiers' section.");
            return;
        }

        ConfigurationSection defaults = configManager.getTiers().getConfigurationSection("settings");
        String defaultMaterial = defaults != null ? defaults.getString("default-tier-material", "BOOK") : "BOOK";
        int defaultAmount = defaults != null ? defaults.getInt("default-tier-amount", 1) : 1;
        boolean defaultGlint = defaults != null && defaults.getBoolean("default-tier-glint", false);
        List<String> defaultFlags = defaults != null ? defaults.getStringList("default-tier-flags") : List.of();

        for (String key : root.getKeys(false)) {
            int tierNumber;
            try {
                tierNumber = Integer.parseInt(key);
            } catch (NumberFormatException ignored) {
                continue;
            }

            String path = "tiers." + key;
            long requiredXp = configManager.getTiers().getLong(path + ".required-xp", tierNumber * 1000L);

            ConfigurationSection item = configManager.getTiers().getConfigurationSection(path + ".item");
            String material = item != null ? item.getString("material", defaultMaterial) : defaultMaterial;
            int amount = item != null ? item.getInt("amount", defaultAmount) : defaultAmount;
            String name = item != null ? item.getString("name", "&eTier " + tierNumber) : "&eTier " + tierNumber;
            List<String> lore = item != null ? item.getStringList("lore") : List.of();
            int customModelData = item != null ? item.getInt("custom-model-data", -1) : -1;
            boolean glint = item != null ? item.getBoolean("glint", defaultGlint) : defaultGlint;
            List<String> flags = item != null ? item.getStringList("flags") : defaultFlags;

            List<String> freeRewards = configManager.getTiers().getStringList(path + ".free.rewards");
            List<String> premiumRewards = configManager.getTiers().getStringList(path + ".premium.rewards");
            List<String> freePreview = configManager.getTiers().getStringList(path + ".free.preview");
            List<String> premiumPreview = configManager.getTiers().getStringList(path + ".premium.preview");

            tiers.add(new Tier(
                    tierNumber,
                    requiredXp,
                    material,
                    amount,
                    name,
                    lore,
                    customModelData,
                    glint,
                    flags,
                    freeRewards,
                    premiumRewards,
                    freePreview,
                    premiumPreview
            ));
        }

        tiers.sort(Comparator.comparingInt(Tier::getNumber));
        plugin.getLogger().info("Loaded " + tiers.size() + " battle pass tiers.");
    }

    public List<Tier> getTiers() {
        return Collections.unmodifiableList(tiers);
    }

    public int getMaxTier() {
        return tiers.isEmpty() ? 0 : tiers.get(tiers.size() - 1).getNumber();
    }

    public PlayerData getPlayerData(UUID uuid) {
        return dataStore.get(uuid);
    }

    public PlayerData getPlayerData(Player player) {
        return getPlayerData(player.getUniqueId());
    }

    public int getCurrentTier(PlayerData data) {
        int current = 0;
        for (Tier tier : tiers) {
            if (data.getXp() >= tier.getRequiredXp()) {
                current = tier.getNumber();
            } else {
                break;
            }
        }
        return current;
    }

    public long getRequiredXpForTier(int tierNumber) {
        Optional<Tier> tier = findTier(tierNumber);
        return tier.map(Tier::getRequiredXp).orElse(0L);
    }

    public Optional<Tier> findTier(int tierNumber) {
        return tiers.stream().filter(t -> t.getNumber() == tierNumber).findFirst();
    }

    public boolean hasPremium(Player player, PlayerData data) {
        boolean usePermission = configManager.getMainConfig().getBoolean("premium.use-permission", true);
        String permission = configManager.getMainConfig().getString("premium.permission", "battlepass.premium");

        if (usePermission && player.hasPermission(permission)) {
            return true;
        }

        if (!usePermission) {
            return data.isPremiumOwned() || player.hasPermission(permission);
        }

        return data.isPremiumOwned();
    }

    public long addXp(Player player, long amount, boolean sendMessage) {
        if (amount <= 0) {
            return getPlayerData(player).getXp();
        }

        PlayerData data = getPlayerData(player);
        int beforeTier = getCurrentTier(data);
        data.addXp(amount);
        int afterTier = getCurrentTier(data);

        if (sendMessage) {
            Map<String, String> placeholders = basePlaceholders(player, data);
            placeholders.put("amount", String.valueOf(amount));
            messages.send(player, "xp-added", placeholders);
        }

        if (afterTier > beforeTier) {
            Map<String, String> placeholders = basePlaceholders(player, data);
            placeholders.put("tier", String.valueOf(afterTier));
            messages.send(player, "tier-up", placeholders);
        }

        dataStore.save(data);
        return data.getXp();
    }

    public long setXp(Player player, long amount, boolean sendMessage) {
        PlayerData data = getPlayerData(player);
        data.setXp(amount);
        if (sendMessage) {
            Map<String, String> placeholders = basePlaceholders(player, data);
            placeholders.put("amount", String.valueOf(data.getXp()));
            messages.send(player, "xp-set", placeholders);
        }
        dataStore.save(data);
        return data.getXp();
    }

    public long removeXp(Player player, long amount, boolean sendMessage) {
        if (amount <= 0) {
            return getPlayerData(player).getXp();
        }

        PlayerData data = getPlayerData(player);
        data.setXp(Math.max(0, data.getXp() - amount));

        if (sendMessage) {
            Map<String, String> placeholders = basePlaceholders(player, data);
            placeholders.put("amount", String.valueOf(amount));
            messages.send(player, "xp-removed", placeholders);
        }

        dataStore.save(data);
        return data.getXp();
    }

    public void setPremiumOwned(UUID playerId, boolean value) {
        PlayerData data = dataStore.get(playerId);
        data.setPremiumOwned(value);
        dataStore.save(data);
    }

    public ClaimResult claim(Player player, int tierNumber, RewardTrack track) {
        return claim(player, tierNumber, track, true);
    }

    public ClaimResult claim(Player player, int tierNumber, RewardTrack track, boolean announce) {
        Optional<Tier> tierOptional = findTier(tierNumber);
        if (tierOptional.isEmpty()) {
            return ClaimResult.TIER_NOT_FOUND;
        }

        PlayerData data = getPlayerData(player);
        Tier tier = tierOptional.get();

        if (getCurrentTier(data) < tierNumber) {
            return ClaimResult.TIER_LOCKED;
        }

        if (track == RewardTrack.PREMIUM && !hasPremium(player, data)) {
            return ClaimResult.NO_PREMIUM;
        }

        if (data.hasClaimed(tierNumber, track)) {
            return ClaimResult.ALREADY_CLAIMED;
        }

        List<String> commands = track == RewardTrack.FREE ? tier.getFreeRewards() : tier.getPremiumRewards();
        if (commands.isEmpty()) {
            return ClaimResult.NO_REWARDS;
        }

        executeRewards(player, tier, track, commands);
        data.setClaimed(tierNumber, track);
        dataStore.save(data);

        Map<String, String> placeholders = basePlaceholders(player, data);
        placeholders.put("tier", String.valueOf(tierNumber));
        placeholders.put("track", track.name().toLowerCase());
        if (announce) {
            if (track == RewardTrack.FREE) {
                messages.send(player, "claimed-free", placeholders);
            } else {
                messages.send(player, "claimed-premium", placeholders);
            }
        }

        return ClaimResult.SUCCESS;
    }

    public int claimAll(Player player, RewardTrack track, Collection<Tier> candidateTiers) {
        int claimed = 0;
        for (Tier tier : candidateTiers) {
            ClaimResult result = claim(player, tier.getNumber(), track, false);
            if (result == ClaimResult.SUCCESS) {
                claimed++;
            }
        }
        return claimed;
    }

    private void executeRewards(Player player, Tier tier, RewardTrack track, List<String> commands) {
        ConsoleCommandSender console = Bukkit.getConsoleSender();
        PlayerData data = getPlayerData(player);

        Map<String, String> placeholders = basePlaceholders(player, data);
        placeholders.put("tier", String.valueOf(tier.getNumber()));
        placeholders.put("required_xp", String.valueOf(tier.getRequiredXp()));
        placeholders.put("track", track.name().toLowerCase());

        for (String rawCommand : commands) {
            String command = PlaceholderUtil.apply(rawCommand, placeholders);
            Bukkit.dispatchCommand(console, command);
        }
    }

    public Map<String, String> basePlaceholders(Player player, PlayerData data) {
        int currentTier = getCurrentTier(data);
        long nextRequired = 0;

        for (Tier tier : tiers) {
            if (tier.getNumber() > currentTier) {
                nextRequired = tier.getRequiredXp();
                break;
            }
        }

        long progressToNext = nextRequired == 0 ? 0 : Math.max(0, nextRequired - data.getXp());

        Map<String, String> placeholders = new HashMap<>();
        placeholders.put("player", player.getName());
        placeholders.put("xp", String.valueOf(data.getXp()));
        placeholders.put("tier", String.valueOf(currentTier));
        placeholders.put("max_tier", String.valueOf(getMaxTier()));
        placeholders.put("next_tier_xp", String.valueOf(nextRequired));
        placeholders.put("xp_to_next", String.valueOf(progressToNext));
        return placeholders;
    }
}
