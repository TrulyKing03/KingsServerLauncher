package com.battlepass.plugin;

import com.battlepass.plugin.command.BattlePassCommand;
import com.battlepass.plugin.config.ConfigManager;
import com.battlepass.plugin.data.PlayerDataStore;
import com.battlepass.plugin.gui.BattlePassGui;
import com.battlepass.plugin.listener.PlayerConnectionListener;
import com.battlepass.plugin.listener.ProgressionListener;
import com.battlepass.plugin.service.BattlePassService;
import com.battlepass.plugin.service.MessageService;
import org.bukkit.command.PluginCommand;
import org.bukkit.scheduler.BukkitTask;
import org.bukkit.plugin.java.JavaPlugin;

public final class BattlePassPlugin extends JavaPlugin {

    private ConfigManager configManager;
    private PlayerDataStore dataStore;
    private MessageService messageService;
    private BattlePassService battlePassService;
    private BattlePassGui battlePassGui;
    private ProgressionListener progressionListener;

    private BukkitTask autosaveTask;

    @Override
    public void onEnable() {
        if (!getDataFolder().exists() && !getDataFolder().mkdirs()) {
            getLogger().warning("Could not create plugin data folder.");
        }

        configManager = new ConfigManager(this);
        configManager.initialize();

        dataStore = new PlayerDataStore(this);
        messageService = new MessageService(configManager);
        battlePassService = new BattlePassService(this, configManager, dataStore, messageService);
        battlePassService.reload();

        battlePassGui = new BattlePassGui(this, configManager, battlePassService, messageService);
        progressionListener = new ProgressionListener(this, configManager, battlePassService);

        getServer().getPluginManager().registerEvents(new PlayerConnectionListener(this, dataStore), this);
        getServer().getPluginManager().registerEvents(battlePassGui, this);
        getServer().getPluginManager().registerEvents(progressionListener, this);

        progressionListener.reload();
        startAutosaveTask();

        PluginCommand command = getCommand("battlepass");
        if (command != null) {
            BattlePassCommand executor = new BattlePassCommand(
                    battlePassService,
                    battlePassGui,
                    messageService,
                    this::reloadPlugin
            );
            command.setExecutor(executor);
            command.setTabCompleter(executor);
        } else {
            getLogger().warning("Command 'battlepass' is not registered in plugin.yml.");
        }

        getLogger().info("BattlePass enabled successfully.");
    }

    @Override
    public void onDisable() {
        if (autosaveTask != null) {
            autosaveTask.cancel();
            autosaveTask = null;
        }

        if (progressionListener != null) {
            progressionListener.shutdown();
        }

        if (dataStore != null) {
            dataStore.saveAll();
        }
    }

    public void reloadPlugin() {
        configManager.reload();
        battlePassService.reload();
        progressionListener.reload();
        startAutosaveTask();
    }

    private void startAutosaveTask() {
        if (autosaveTask != null) {
            autosaveTask.cancel();
            autosaveTask = null;
        }

        int seconds = Math.max(30, configManager.getMainConfig().getInt("storage.autosave-interval-seconds", 120));
        autosaveTask = getServer().getScheduler().runTaskTimer(this, () -> {
            if (dataStore != null) {
                dataStore.saveAll();
            }
        }, seconds * 20L, seconds * 20L);
    }

    public ConfigManager getConfigManager() {
        return configManager;
    }

    public BattlePassService getBattlePassService() {
        return battlePassService;
    }

    public MessageService getMessageService() {
        return messageService;
    }

    public PlayerDataStore getDataStore() {
        return dataStore;
    }

    public BattlePassGui getBattlePassGui() {
        return battlePassGui;
    }
}
