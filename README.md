# Kiro-Pipe, an interceptor that allows you to use Kiro with external API's

...in theory, as it is unfinished and needs further testing.

The project is *technically usable*, the python script and folder should be placed alongside Kiro.exe, and then launched, which will then employ a MITM and node wizardry to cancel out the SSL checks and errors, then make itself look as if it were AWS' servers.

On its current iteration, the model routing is implemented, and new models and mock ones can be dynamically added, in addition to manipulating many of the variables.


The *actual* usability of this, remains iffy. You can use the Kiro IDE as you otherwise would, and see and intercept the logs with debug_mode on TRUE, but the conversion into the Anthropic format is not entirely tested nor validated, and needs more work.
In addition, the original plan was to integrate AWS Q with LiteLLM with a custom translation layer, but that flopped over the stacked inefficiencies, delays, having to hold and juggle the network traffic to try and match the rate limits of weaker models that don't quite follow nicely on Amazon's dynamics...

It's a work in progress.

Feel free to use this or contribute, if you think you can help! I'll likely get back to it, as I see much potential on being able to use Kiro IDE's suite with a local LLM, which is the expected case of use for any of those interested in this.
As for when I get back into this project, if no contribution has been made by then, I'll likely rebuilt it in Node.js with Mockttp and Portkey instead.
