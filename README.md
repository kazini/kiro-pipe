# Kiro-Pipe, an interceptor that allows you to use Kiro with external API's

...in theory.

I started making this over the course of two days and quickly became incredibly frustrated over the choice of architecture and the code quality.

The risks of using AI are often exactly this -- A messy codebase and not being able to keep your internals organized and tracked as you should, especially if you iterate fast, and as much as I usually use it as an aide and not a detriment... this time, I have reaped the price.

The project is *technically usable*, the python script and folder should be placed alongside Kiro.exe, and then launched, which will then employ a MITM and node wizardry to cancel out the SSL checks and errors, then make itself look as if it were AWS' servers.

On its current iteration, the model routing is implemented, and new models and mock ones can be dynamically added, in addition to manipulating many of the variables.


The *actual* usability of this, remains iffy. You can use the Kiro IDE as you otherwise would, and see and intercept the logs with debug_mode on TRUE, but the conversion into the Anthropic format are not entirely tested nor validated, and need work.
In addition, the original plan was to integrate AWS Q with LiteLLM with a custom translation layer, but that flopped over the stacked inefficiencies, delays, having to hold and juggle the network traffic to try and match the rate limits of weaker models that don't quite follow nicely on Amazon's dynamics...

It's a work in progress.
It didn't help that I accidentally lost four hours of work in adding a dynamic and detailed model mapping and routing system that tracked costs and manipulated the client via network requests, and did a surprisingly okay job at integrating AWS Q with LiteLLM on the last trek, despite the incredibly obtuse nature of it when trying to use it as an SDK for this type of high speed operations.


Feel free to use this or contribute, if you think you can help! I'll likely get back to it, as I see much potential on being able to use Kiro IDE's suite with a local LLM, which is the expected case of use for any of those interested in this.
As for when I get back into this project, if no contribution has been made by then, I'll likely rebuilt it in Node.js with Mockttp and Portkey instead.

Happy hunting!
