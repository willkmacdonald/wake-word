# Architecture

The architecture is endpoint -> controlled Azure gateway -> Microsoft transcription.

The endpoint streams no audio before local wake-word activation. After activation, it opens an authenticated websocket session to the gateway and sends post-trigger audio frames.
