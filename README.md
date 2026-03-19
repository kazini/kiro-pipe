# Kiro-Pipe, an interceptor that allows you to use Kiro with external API's

The python script and folder should be placed alongside Kiro.exe, and then launched, which will then employ a MITM and node wizardry to cancel out the SSL checks and errors, then make itself look as if it were AWS' servers.

*The project is in need of polish and testing*. On its current iteration, the model routing is implemented, and new models and mock ones can be dynamically added, in addition to manipulating many of the variables. It may work on some services and some models. OpenRouter and local OpenAI currently work fine.

The original plan was to integrate AWS Q with LiteLLM with a custom translation layer, but that flopped over the stacked inefficiencies, delays, having to hold and juggle the network traffic to try and match the rate limits of weaker models that don't quite follow nicely on Amazon's dynamics... LiteLLM directintegration should technically work but needs actual testing and validation.

The folder _kiro-mask contains a separate work-in-progress iteration in node.js, but it is incomplete and non-functional, so you may safely delete it and use the rest.

Feel free to use this or contribute, if you think you can help! I'll likely get back to it, as I see much potential on being able to use Kiro IDE's suite with a local LLM, which is the expected case of use for any of those interested in this.
