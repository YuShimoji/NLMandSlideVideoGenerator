const { contextBridge } = require('electron');

// Expose minimal API to renderer (currently none needed since Streamlit runs in an iframe-like context)
contextBridge.exposeInMainWorld('nlmApp', {
    version: '1.0.0',
    name: 'NLM Slide Video Generator',
});
