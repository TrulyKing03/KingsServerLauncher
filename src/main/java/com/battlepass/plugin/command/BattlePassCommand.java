package com.battlepass.plugin.command;

import com.battlepass.plugin.gui.BattlePassGui;
import com.battlepass.plugin.model.RewardTrack;
import com.battlepass.plugin.service.BattlePassService;
import com.battlepass.plugin.service.ClaimResult;
import com.battlepass.plugin.service.MessageService;
import org.bukkit.Bukkit;
import org.bukkit.command.Command;
import org.bukkit.command.CommandExecutor;
import org.bukkit.command.CommandSender;
import org.bukkit.command.TabCompleter;
import org.bukkit.entity.Player;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.stream.Collectors;

public final class BattlePassCommand implements CommandExecutor, TabCompleter {

    private final BattlePassService battlePassService;
    private final BattlePassGui gui;
    private final MessageService messages;
    private final Runnable reloadAction;

    public BattlePassCommand(BattlePassService battlePassService, BattlePassGui gui, MessageService messages, Runnable reloadAction) {
        this.battlePassService = battlePassService;
        this.gui = gui;
        this.messages = messages;
        this.reloadAction = reloadAction;
    }

    @Override
    public boolean onCommand(CommandSender sender, Command command, String label, String[] args) {
        if (args.length == 0) {
            if (!(sender instanceof Player player)) {
                messages.send(sender, "players-only");
                return true;
            }
            if (!player.hasPermission("battlepass.use")) {
                messages.send(player, "no-permission");
                return true;
            }
            gui.open(player, 1);
            return true;
        }

        String sub = args[0].toLowerCase(Locale.ROOT);
        switch (sub) {
            case "open" -> handleOpen(sender, args);
            case "reload" -> handleReload(sender);
            case "addxp" -> handleXpChange(sender, args, "add");
            case "setxp" -> handleXpChange(sender, args, "set");
            case "removexp" -> handleXpChange(sender, args, "remove");
            case "premium" -> handlePremium(sender, args);
            case "info" -> handleInfo(sender, args);
            case "claim" -> handleClaim(sender, args);
            case "help" -> sendHelp(sender);
            default -> messages.send(sender, "unknown-command");
        }

        return true;
    }

    private void handleOpen(CommandSender sender, String[] args) {
        if (args.length == 1) {
            if (!(sender instanceof Player player)) {
                messages.send(sender, "players-only");
                return;
            }

            if (!player.hasPermission("battlepass.use")) {
                messages.send(player, "no-permission");
                return;
            }

            gui.open(player, 1);
            return;
        }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            messages.send(sender, "player-not-found", Map.of("player", args[1]));
            return;
        }

        int page = 1;
        if (args.length >= 3) {
            Integer parsed = parseInt(args[2]);
            if (parsed == null || parsed <= 0) {
                messages.send(sender, "invalid-number", Map.of("value", args[2]));
                return;
            }
            page = parsed;
        }

        if (sender.equals(target)) {
            if (!target.hasPermission("battlepass.use")) {
                messages.send(sender, "no-permission");
                return;
            }
        } else if (!sender.hasPermission("battlepass.admin")) {
            messages.send(sender, "no-permission");
            return;
        }

        gui.open(target, page);
        if (!sender.equals(target)) {
            messages.send(sender, "opened-for-player", Map.of("player", target.getName(), "page", String.valueOf(page)));
        }
    }

    private void handleReload(CommandSender sender) {
        if (!sender.hasPermission("battlepass.admin")) {
            messages.send(sender, "no-permission");
            return;
        }

        reloadAction.run();
        messages.send(sender, "reloaded");
    }

    private void handleXpChange(CommandSender sender, String[] args, String mode) {
        if (!sender.hasPermission("battlepass.admin")) {
            messages.send(sender, "no-permission");
            return;
        }

        if (args.length < 3) {
            messages.send(sender, "usage-xp");
            return;
        }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            messages.send(sender, "player-not-found", Map.of("player", args[1]));
            return;
        }

        Long amount = parseLong(args[2]);
        if (amount == null || amount < 0) {
            messages.send(sender, "invalid-number", Map.of("value", args[2]));
            return;
        }

        long newXp;
        switch (mode) {
            case "add" -> newXp = battlePassService.addXp(target, amount, true);
            case "set" -> newXp = battlePassService.setXp(target, amount, true);
            case "remove" -> newXp = battlePassService.removeXp(target, amount, true);
            default -> {
                return;
            }
        }

        messages.send(sender, "xp-admin-updated", Map.of(
                "player", target.getName(),
                "xp", String.valueOf(newXp),
                "amount", String.valueOf(amount)
        ));
    }

    private void handlePremium(CommandSender sender, String[] args) {
        if (!sender.hasPermission("battlepass.admin")) {
            messages.send(sender, "no-permission");
            return;
        }

        if (args.length < 3) {
            messages.send(sender, "usage-premium");
            return;
        }

        Player target = Bukkit.getPlayerExact(args[1]);
        if (target == null) {
            messages.send(sender, "player-not-found", Map.of("player", args[1]));
            return;
        }

        if (!args[2].equalsIgnoreCase("true") && !args[2].equalsIgnoreCase("false")) {
            messages.send(sender, "invalid-boolean", Map.of("value", args[2]));
            return;
        }

        boolean value = Boolean.parseBoolean(args[2]);
        battlePassService.setPremiumOwned(target.getUniqueId(), value);

        messages.send(sender, "premium-set-admin", Map.of("player", target.getName(), "value", String.valueOf(value)));
        messages.send(target, "premium-set-player", Map.of("value", String.valueOf(value)));
    }

    private void handleInfo(CommandSender sender, String[] args) {
        Player target;
        if (args.length >= 2) {
            target = Bukkit.getPlayerExact(args[1]);
            if (target == null) {
                messages.send(sender, "player-not-found", Map.of("player", args[1]));
                return;
            }
            if (!sender.equals(target) && !sender.hasPermission("battlepass.admin")) {
                messages.send(sender, "no-permission");
                return;
            }
        } else {
            if (!(sender instanceof Player player)) {
                messages.send(sender, "players-only");
                return;
            }
            target = player;
        }

        var data = battlePassService.getPlayerData(target);
        int currentTier = battlePassService.getCurrentTier(data);
        boolean premium = battlePassService.hasPremium(target, data);

        messages.send(sender, "info-header", Map.of("player", target.getName()));
        messages.send(sender, "info-xp", Map.of("xp", String.valueOf(data.getXp())));
        messages.send(sender, "info-tier", Map.of("tier", String.valueOf(currentTier), "max_tier", String.valueOf(battlePassService.getMaxTier())));
        messages.send(sender, "info-premium", Map.of("premium", String.valueOf(premium)));
    }

    private void handleClaim(CommandSender sender, String[] args) {
        if (!(sender instanceof Player player)) {
            messages.send(sender, "players-only");
            return;
        }

        if (args.length < 3) {
            messages.send(sender, "usage-claim");
            return;
        }

        Integer tier = parseInt(args[1]);
        if (tier == null || tier <= 0) {
            messages.send(sender, "invalid-number", Map.of("value", args[1]));
            return;
        }

        RewardTrack track;
        if (args[2].equalsIgnoreCase("free")) {
            track = RewardTrack.FREE;
        } else if (args[2].equalsIgnoreCase("premium")) {
            track = RewardTrack.PREMIUM;
        } else {
            messages.send(sender, "usage-claim");
            return;
        }

        ClaimResult result = battlePassService.claim(player, tier, track);
        switch (result) {
            case SUCCESS -> {
            }
            case TIER_NOT_FOUND -> messages.send(player, "tier-not-found", Map.of("tier", String.valueOf(tier)));
            case TIER_LOCKED -> messages.send(player, "tier-locked", Map.of("tier", String.valueOf(tier)));
            case ALREADY_CLAIMED -> messages.send(player, "already-claimed", Map.of("tier", String.valueOf(tier), "track", track.name().toLowerCase()));
            case NO_PREMIUM -> messages.send(player, "premium-required", Map.of("tier", String.valueOf(tier)));
            case NO_REWARDS -> messages.send(player, "no-rewards", Map.of("tier", String.valueOf(tier), "track", track.name().toLowerCase()));
        }
    }

    private void sendHelp(CommandSender sender) {
        messages.send(sender, "help-1");
        messages.send(sender, "help-2");
        messages.send(sender, "help-3");
        messages.send(sender, "help-4");
        messages.send(sender, "help-5");
        messages.send(sender, "help-6");
    }

    @Override
    public List<String> onTabComplete(CommandSender sender, Command command, String alias, String[] args) {
        if (args.length == 1) {
            List<String> base = new ArrayList<>(List.of("open", "info", "claim", "help"));
            if (sender.hasPermission("battlepass.admin")) {
                base.addAll(List.of("reload", "addxp", "setxp", "removexp", "premium"));
            }
            return filter(base, args[0]);
        }

        if (args.length == 2) {
            String sub = args[0].toLowerCase(Locale.ROOT);
            if (sub.equals("open") || sub.equals("addxp") || sub.equals("setxp") || sub.equals("removexp") || sub.equals("premium") || sub.equals("info")) {
                return filter(Bukkit.getOnlinePlayers().stream().map(Player::getName).collect(Collectors.toList()), args[1]);
            }
            if (sub.equals("claim")) {
                return filter(List.of("1", "2", "3", "10", "50", "100"), args[1]);
            }
        }

        if (args.length == 3) {
            String sub = args[0].toLowerCase(Locale.ROOT);
            if (sub.equals("open")) {
                return filter(List.of("1", "2", "3", "4"), args[2]);
            }
            if (sub.equals("premium")) {
                return filter(List.of("true", "false"), args[2]);
            }
            if (sub.equals("claim")) {
                return filter(List.of("free", "premium"), args[2]);
            }
        }

        return Collections.emptyList();
    }

    private List<String> filter(List<String> values, String input) {
        String lowered = input.toLowerCase(Locale.ROOT);
        return values.stream()
                .filter(value -> value.toLowerCase(Locale.ROOT).startsWith(lowered))
                .collect(Collectors.toList());
    }

    private Integer parseInt(String raw) {
        try {
            return Integer.parseInt(raw);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private Long parseLong(String raw) {
        try {
            return Long.parseLong(raw);
        } catch (NumberFormatException ignored) {
            return null;
        }
    }
}
