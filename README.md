# Kiro-Pipe, an interceptor that allows you to use Kiro with external API's

The python script and folder should be placed alongside Kiro.exe, and then launched, which will then employ a MITM and node wizardry to cancel out the SSL checks and errors, then make itself look as if it were AWS' servers.

*The project is in need of polish and testing*. On its current iteration, the model routing is implemented, and new models and mock ones can be dynamically added, in addition to manipulating many of the variables. It may work on some services and some models. OpenRouter and local OpenAI currently work fine.

The original plan was to integrate AWS Q with LiteLLM with a custom translation layer, but that flopped over the stacked inefficiencies, delays, having to hold and juggle the network traffic to try and match the rate limits of weaker models that don't quite follow nicely on Amazon's dynamics... LiteLLM directintegration should technically work but needs actual testing and validation.

The folder _kiro-mask contains a separate work-in-progress iteration in node.js, but it is incomplete and non-functional, so you may safely delete it and use the rest.

Feel free to use this or contribute, if you think you can help! I'll likely get back to it, as I see much potential on being able to use Kiro IDE's suite with a local LLM, which is the expected case of use for any of those interested in this.


#### To-Do List:
```
! figure out that 0.01 credits spent even with custom models, *apparently it even gets tallied when the code supposedly blocks the authentication login and every other request*, insane.

> test custom completions model
	* fix, not behaving as expected with custom 'current' option, untested custom specified | must set up so it routes to models correctly instead of fake-blocking with other traffic
> trim back search tool parameters to 'default', 'enforced' and 'disabled', removing the extra dict and special options (except, perhaps, description and existing parameter replacement... if they are even made to work... so just remove the Execute and anything within? and ensure partial overrides work well)


> test max context usage and compression
	* context usage seems to not be calculated based on total chat or sent context size, but on the recently sent message alone? must fix
> test if Anthropic format translates correctly, in full live tests and not just automated

- system prompt injector with priority based on labels, replace current "entire prompt" swap, the system prompt is built dynamically before sending via network -- these should go into a file, then specified in the config as to their location (default "steering" folder in _kiropipe folder)

- improve target selector for free models vs finding usage for credit and context calculation
- remove "credits used" for custom models.
- make sure that debug messages and regular messages are differentiated / some regular messages should definitely only be showing up under debug, methinks.




ERRORS:
gemini 2.5 pro issue:
tool (tool_call_id: readFile-1773959509523935100-4)
     Content: Error: Provided input does not match the required ...

may be related to 2.5 flash issues. could delve into direct. perhaps it was an issue on my proxy side between openai and gemini formats.
```