# Unifier plugin template
This is a template repository you can use to write plugins for Unifier.

> [!NOTE]
> Once you have read through everything below and know what you're doing, you're free to replace
> this README file with whatever you want.

## plugin.json
plugin.json contains the metadata of your plugin, such as the plugin ID, name, etc. Unifier will
read this file on boot, so it knows which files to load to load your plugin.

Below are the list of values you may have in your plugin.json file. Unless otherwise stated, all
keys are compatible with Unifier **v1.2.0** (release 36) and newer.

### `id`
Plugin ID. Unifier uses this as the identifier for your plugin, and no plugin
installed to your bot may have the same ID. Users will need to specify the ID as the plugin when
running install, uninstall, and upgrade for plugins.

### `name`
Plugin name. Unlike plugin IDs, this can be whatever you desire.

### `description`
Plugin description. Describe what your plugin does here.

### `version`
Plugin version. We recommend you follow [semantic versioning](https://semver.org/) for this.

### `release`
Plugin release number. Unifier will use this to tell if the plugin is up to date or not.

### `minimum`
The minimum Unifier release required to use your plugin.

### `services` (v1.2.3+/rel43+)
> [!WARNING]
> We haven't documented this yet, but we will in the near future.

Services your plugin will provide. Instance owners will need to review and allow services in order 
for the plugin to be installed. Services include:
- `content_protection`: Plugin provides content filtering. Grants access to message content and
  moderation actions.
- `content_processing`: Plugin provides content processing (e.g. message stylizing). Grants access
  to message content.
- `emojis` (v2.0.1+/rel51+): Plugin provides an emoji pack. An emoji.json file must be present, as
  well as emojis (can be images or GIFs) in an emojis folder.
> [!WARNING]
> If `services` is not empty, you will need to have a file called `[plugin_id]_[service].py` that
> provides the service, and it should be added in `utils`.

### `requirements` (v1.2.0-patch2+/rel38+)
Dependencies the plugin needs other than the ones in Unifier's requirements.txt file.

### `shutdown`
If your plugin needs special code being ran before being unloaded, set this to true.
> [!WARNING]
> If this is true, your plugin will not be able to be unloaded without a `[plugin_id]_check.py`
> file. You will need to specify this in the `utils` key.

### `modules`
Plugin modules. All files in here will be loaded as an extension when loading the plugin.

### `utils`
Plugin utility scripts. If `shutdown` is true, you **must** have `[plugin_id]_check.py` in here.

----

## Examples
Need an example to know what you need to have in your repository? You might want to check out
[unifier-revolt](https://github.com/UnifierHQ/unifier-revolt).

## Installing plugins
To install a plugin, run the `install <repo_url>` command. This will install a plugin from the
Git repository you specified.

## Licensing
As Unifier is AGPLv3 licensed, your plugin must be licensed AGPLv3 as well.
