# CTGP-7 Plugin Server Code
This is the C++ code running in the CTGP-7 plugin to handle all server communications. Keep in mind that the code provided doesn't work as is, and needs to be adapted to the environment you want to use.

### NetHandler Class
This is the main server communications class. It has a few dependencies with [CTRPluginFramework](https://gbatemp.net/threads/ctrpluginframework-blank-plugin-now-with-action-replay.487729/) and [minibson](https://github.com/cyberguijarro/minibson), but can be easily adapted to work on any homebrew environment.

### Net Class
This holds the actual server logic (using the **NetHandler** class to communicate). This part has many dependencies with the rest of the CTGP-7 plugin, but can be used to see an example usage of the handler class.