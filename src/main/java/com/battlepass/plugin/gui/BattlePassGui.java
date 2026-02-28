package com.battlepass.plugin.gui;

import com.battlepass.plugin.BattlePassPlugin;
import com.battlepass.plugin.config.ConfigManager;
import com.battlepass.plugin.data.PlayerData;
import com.battlepass.plugin.model.RewardTrack;
import com.battlepass.plugin.model.Tier;
import com.battlepass.plugin.service.BattlePassService;
import com.battlepass.plugin.service.ClaimResult;
import com.battlepass.plugin.service.MessageService;
import com.battlepass.plugin.util.ColorUtil;
import com.battlepass.plugin.util.ItemUtil;
import com.battlepass.plugin.util.PlaceholderUtil;
import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.Sound;
import org.bukkit.configuration.ConfigurationSection;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.enchantments.Enchantment;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.inventory.ClickType;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.inventory.InventoryDragEvent;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class BattlePassGui implements Listener {

    private static final List<Integer> DEFAULT_TIER_SLOTS = List.of(
            10, 11, 12, 13, 14, 15, 16,
            19, 20, 21, 22, 23, 24, 25,
            28, 29, 30, 31, 32, 33, 34,
            37, 38, 39, 40, 41, 42, 43
    );

    private final BattlePassPlugin plugin;
    private final ConfigManager configManager;
    private final BattlePassService battlePassService;
    private final MessageService messages;

    public BattlePassGui(BattlePassPlugin plugin, ConfigManager configManager, BattlePassService battlePassService, MessageService messages) {
        this.plugin = plugin;
        this.configManager = configManager;
        this.battlePassService = battlePassService;
        this.messages = messages;
    }

    public void open(Player player, int page) {
        FileConfiguration config = configManager.getMainConfig();
        int size = normalizeSize(config.getInt("gui.size", 54));

        List<Integer> tierSlots = config.getIntegerList("gui.tier-slots");
        if (tierSlots.isEmpty()) {
            tierSlots = DEFAULT_TIER_SLOTS;
        }

        List<Tier> tiers = battlePassService.getTiers();
        int tiersPerPage = Math.max(1, tierSlots.size());
        int maxPage = Math.max(1, (int) Math.ceil(tiers.size() / (double) tiersPerPage));
        int safePage = Math.max(1, Math.min(page, maxPage));

        int start = (safePage - 1) * tiersPerPage;
        int end = Math.min(start + tiersPerPage, tiers.size());

        Map<Integer, Integer> slotToTier = new HashMap<>();
        List<Integer> visibleTierIds = new ArrayList<>();

        BattlePassHolder holder = new BattlePassHolder(player.getUniqueId(), safePage, maxPage, slotToTier, visibleTierIds);
        PlayerData data = battlePassService.getPlayerData(player);

        Map<String, String> titlePlaceholders = battlePassService.basePlaceholders(player, data);
        titlePlaceholders.put("page", String.valueOf(safePage));
        titlePlaceholders.put("max_page", String.valueOf(maxPage));

        String title = ColorUtil.colorize(PlaceholderUtil.apply(config.getString("gui.title", "&0Battle Pass"), titlePlaceholders));
        Inventory inventory = Bukkit.createInventory(holder, size, title);
        holder.setInventory(inventory);

        if (config.getBoolean("gui.fill-empty", true)) {
            ConfigurationSection fillerSection = config.getConfigurationSection("gui.filler-item");
            ItemStack filler = ItemUtil.createItem(fillerSection, new ItemStack(Material.GRAY_STAINED_GLASS_PANE), titlePlaceholders);
            for (int slot = 0; slot < size; slot++) {
                inventory.setItem(slot, filler);
            }
        }

        applyStaticItems(inventory, titlePlaceholders);
        placeButtons(player, inventory, safePage, maxPage);

        int index = 0;
        for (int i = start; i < end; i++) {
            Tier tier = tiers.get(i);
            if (index >= tierSlots.size()) {
                break;
            }

            int slot = tierSlots.get(index++);
            if (slot < 0 || slot >= size) {
                continue;
            }

            inventory.setItem(slot, buildTierItem(player, tier, data));
            slotToTier.put(slot, tier.getNumber());
            visibleTierIds.add(tier.getNumber());
        }

        player.openInventory(inventory);
        playConfiguredSound(player, "gui.sounds.open");
    }

    private void applyStaticItems(Inventory inventory, Map<String, String> placeholders) {
        ConfigurationSection staticItems = configManager.getMainConfig().getConfigurationSection("gui.static-items");
        if (staticItems == null) {
            return;
        }

        for (String key : staticItems.getKeys(false)) {
            ConfigurationSection section = staticItems.getConfigurationSection(key);
            if (section == null) {
                continue;
            }

            ConfigurationSection itemSection = section.getConfigurationSection("item");
            ItemStack item = ItemUtil.createItem(itemSection, new ItemStack(Material.BLACK_STAINED_GLASS_PANE), placeholders);
            for (int slot : section.getIntegerList("slots")) {
                if (slot >= 0 && slot < inventory.getSize()) {
                    inventory.setItem(slot, item);
                }
            }
        }
    }

    private void placeButtons(Player player, Inventory inventory, int page, int maxPage) {
        PlayerData data = battlePassService.getPlayerData(player);
        Map<String, String> placeholders = battlePassService.basePlaceholders(player, data);
        placeholders.put("page", String.valueOf(page));
        placeholders.put("max_page", String.valueOf(maxPage));

        placeButton(inventory, "gui.buttons.previous", placeholders);
        placeButton(inventory, "gui.buttons.next", placeholders);
        placeButton(inventory, "gui.buttons.close", placeholders);
        placeButton(inventory, "gui.buttons.info", placeholders);
        placeButton(inventory, "gui.buttons.claim-all-free", placeholders);
        placeButton(inventory, "gui.buttons.claim-all-premium", placeholders);
    }

    private void placeButton(Inventory inventory, String path, Map<String, String> placeholders) {
        ConfigurationSection section = configManager.getMainConfig().getConfigurationSection(path);
        if (section == null) {
            return;
        }

        int slot = section.getInt("slot", -1);
        if (slot < 0 || slot >= inventory.getSize()) {
            return;
        }

        ConfigurationSection itemSection = section.getConfigurationSection("item");
        ItemStack fallback = new ItemStack(Material.STONE_BUTTON);
        ItemStack item = ItemUtil.createItem(itemSection, fallback, placeholders);
        inventory.setItem(slot, item);
    }

    private ItemStack buildTierItem(Player player, Tier tier, PlayerData data) {
        Material material = Material.matchMaterial(tier.getMaterial());
        if (material == null) {
            material = Material.BOOK;
        }

        ItemStack item = new ItemStack(material, Math.max(1, Math.min(64, tier.getAmount())));
        ItemMeta meta = item.getItemMeta();
        if (meta == null) {
            return item;
        }

        int currentTier = battlePassService.getCurrentTier(data);
        boolean unlocked = currentTier >= tier.getNumber();
        boolean hasPremium = battlePassService.hasPremium(player, data);

        boolean freeClaimed = data.hasClaimed(tier.getNumber(), RewardTrack.FREE);
        boolean premiumClaimed = data.hasClaimed(tier.getNumber(), RewardTrack.PREMIUM);
        boolean premiumHasRewards = !tier.getPremiumRewards().isEmpty();

        String state = unlocked ? "claimable" : "locked";
        if (unlocked && freeClaimed && (!premiumHasRewards || premiumClaimed || !hasPremium)) {
            state = "claimed";
        }

        Map<String, String> placeholders = battlePassService.basePlaceholders(player, data);
        placeholders.put("tier", String.valueOf(tier.getNumber()));
        placeholders.put("required_xp", String.valueOf(tier.getRequiredXp()));
        placeholders.put("track", "both");

        String prefix = configManager.getMainConfig().getString("gui.tier-status." + state + ".prefix", "");
        String displayName = PlaceholderUtil.apply(prefix + tier.getName(), placeholders);
        meta.setDisplayName(ColorUtil.colorize(displayName));

        List<String> lore = new ArrayList<>();
        for (String raw : tier.getLore()) {
            lore.add(ColorUtil.colorize(PlaceholderUtil.apply(raw, placeholders)));
        }

        String separator = configManager.getMainConfig().getString("gui.lore.separator", "&8&m----------------");
        lore.add(ColorUtil.colorize(separator));
        lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.free-header", "&aFree Track")));

        if (tier.getFreePreview().isEmpty()) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.no-free-rewards", "&7No free reward.")));
        } else {
            for (String line : tier.getFreePreview()) {
                lore.add(ColorUtil.colorize(PlaceholderUtil.apply(line, placeholders)));
            }
        }

        if (!unlocked) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.free-locked", "&8Locked")));
        } else if (freeClaimed) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.free-claimed", "&7Already claimed")));
        } else {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.free-claimable", "&aLeft click to claim")));
        }

        lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-header", "&6Premium Track")));

        if (tier.getPremiumPreview().isEmpty()) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.no-premium-rewards", "&7No premium reward.")));
        } else {
            for (String line : tier.getPremiumPreview()) {
                lore.add(ColorUtil.colorize(PlaceholderUtil.apply(line, placeholders)));
            }
        }

        if (!premiumHasRewards) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-empty", "&7No premium reward for this tier.")));
        } else if (!hasPremium) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-no-access", "&cRequires premium pass")));
        } else if (!unlocked) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-locked", "&8Locked")));
        } else if (premiumClaimed) {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-claimed", "&7Already claimed")));
        } else {
            lore.add(ColorUtil.colorize(configManager.getMainConfig().getString("gui.lore.premium-claimable", "&6Right click to claim")));
        }

        for (String hint : configManager.getMainConfig().getStringList("gui.lore.click-hints")) {
            lore.add(ColorUtil.colorize(PlaceholderUtil.apply(hint, placeholders)));
        }

        meta.setLore(lore);

        if (tier.getCustomModelData() >= 0) {
            meta.setCustomModelData(tier.getCustomModelData());
        }

        for (String rawFlag : tier.getFlags()) {
            try {
                meta.addItemFlags(ItemFlag.valueOf(rawFlag.toUpperCase()));
            } catch (IllegalArgumentException ignored) {
            }
        }

        boolean glint = tier.isGlint();
        if (state.equals("claimable") && configManager.getMainConfig().getBoolean("gui.tier-status.claimable.force-glint", true)) {
            glint = true;
        }

        if (glint) {
            meta.addEnchant(Enchantment.UNBREAKING, 1, true);
            meta.addItemFlags(ItemFlag.HIDE_ENCHANTS);
        }

        item.setItemMeta(meta);
        return item;
    }

    @EventHandler
    public void onInventoryClick(InventoryClickEvent event) {
        if (!(event.getView().getTopInventory().getHolder() instanceof BattlePassHolder holder)) {
            return;
        }

        event.setCancelled(true);
        if (!(event.getWhoClicked() instanceof Player player)) {
            return;
        }

        if (!player.getUniqueId().equals(holder.getViewer())) {
            return;
        }

        int rawSlot = event.getRawSlot();
        if (rawSlot < 0 || rawSlot >= event.getView().getTopInventory().getSize()) {
            return;
        }

        FileConfiguration config = configManager.getMainConfig();

        int closeSlot = config.getInt("gui.buttons.close.slot", -1);
        int prevSlot = config.getInt("gui.buttons.previous.slot", -1);
        int nextSlot = config.getInt("gui.buttons.next.slot", -1);
        int claimFreeSlot = config.getInt("gui.buttons.claim-all-free.slot", -1);
        int claimPremiumSlot = config.getInt("gui.buttons.claim-all-premium.slot", -1);

        if (rawSlot == closeSlot) {
            player.closeInventory();
            return;
        }

        if (rawSlot == prevSlot) {
            Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.getPage() - 1));
            return;
        }

        if (rawSlot == nextSlot) {
            Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.getPage() + 1));
            return;
        }

        if (rawSlot == claimFreeSlot) {
            claimVisible(player, holder, RewardTrack.FREE);
            Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.getPage()));
            return;
        }

        if (rawSlot == claimPremiumSlot) {
            claimVisible(player, holder, RewardTrack.PREMIUM);
            Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.getPage()));
            return;
        }

        Integer tierId = holder.getTierForSlot(rawSlot);
        if (tierId == null) {
            return;
        }

        RewardTrack track = event.getClick().isRightClick() ? RewardTrack.PREMIUM : RewardTrack.FREE;

        if (event.getClick() == ClickType.SHIFT_LEFT) {
            claimVisible(player, holder, RewardTrack.FREE);
        } else if (event.getClick() == ClickType.SHIFT_RIGHT) {
            claimVisible(player, holder, RewardTrack.PREMIUM);
        } else {
            claimSingle(player, tierId, track);
        }

        Bukkit.getScheduler().runTask(plugin, () -> open(player, holder.getPage()));
    }

    @EventHandler
    public void onInventoryDrag(InventoryDragEvent event) {
        if (event.getView().getTopInventory().getHolder() instanceof BattlePassHolder) {
            event.setCancelled(true);
        }
    }

    private void claimSingle(Player player, int tierId, RewardTrack track) {
        ClaimResult result = battlePassService.claim(player, tierId, track);
        switch (result) {
            case SUCCESS -> playConfiguredSound(player, "gui.sounds.claim");
            case TIER_NOT_FOUND -> messages.send(player, "tier-not-found", Map.of("tier", String.valueOf(tierId)));
            case TIER_LOCKED -> messages.send(player, "tier-locked", Map.of("tier", String.valueOf(tierId)));
            case ALREADY_CLAIMED -> messages.send(player, "already-claimed", Map.of("tier", String.valueOf(tierId), "track", track.name().toLowerCase()));
            case NO_PREMIUM -> messages.send(player, "premium-required", Map.of("tier", String.valueOf(tierId)));
            case NO_REWARDS -> messages.send(player, "no-rewards", Map.of("tier", String.valueOf(tierId), "track", track.name().toLowerCase()));
        }
    }

    private void claimVisible(Player player, BattlePassHolder holder, RewardTrack track) {
        List<Tier> visible = new ArrayList<>();
        for (Integer tierId : holder.getVisibleTiers()) {
            Optional<Tier> tier = battlePassService.findTier(tierId);
            tier.ifPresent(visible::add);
        }

        int claimed = battlePassService.claimAll(player, track, visible);
        if (claimed <= 0) {
            messages.send(player, "claim-all-none", Map.of("track", track.name().toLowerCase()));
            return;
        }

        playConfiguredSound(player, "gui.sounds.claim");
        messages.send(player, "claim-all-success", Map.of(
                "count", String.valueOf(claimed),
                "track", track.name().toLowerCase()
        ));
    }

    private int normalizeSize(int size) {
        int clamped = Math.max(9, Math.min(54, size));
        return clamped - (clamped % 9);
    }

    private void playConfiguredSound(Player player, String path) {
        ConfigurationSection section = configManager.getMainConfig().getConfigurationSection(path);
        if (section == null || !section.getBoolean("enabled", false)) {
            return;
        }

        String rawSound = section.getString("type", "UI_BUTTON_CLICK");
        float volume = (float) section.getDouble("volume", 1.0D);
        float pitch = (float) section.getDouble("pitch", 1.0D);

        try {
            Sound sound = Sound.valueOf(rawSound.toUpperCase());
            player.playSound(player.getLocation(), sound, volume, pitch);
        } catch (IllegalArgumentException ignored) {
        }
    }
}
