/**
 * VitalSync - Node-RED Settings
 * Configuración para el simulador IoT de signos vitales
 */

module.exports = {
    // Puerto HTTP
    uiPort: process.env.PORT || 1880,

    // Host para escuchar
    uiHost: "0.0.0.0",

    // Deshabilitar editor en producción (cambiar a true para bloquear)
    disableEditor: false,

    // Flows file
    flowFile: 'flows.json',

    // User directory
    userDir: '/data',

    // Logging
    logging: {
        console: {
            level: "info",
            metrics: false,
            audit: false
        }
    },

    // Editor theme
    editorTheme: {
        projects: {
            enabled: false
        },
        header: {
            title: "VitalSync IoT Simulator"
        }
    },

    // Function node settings
    functionGlobalContext: {
        // Variables globales disponibles en nodos function
        vitalsyncApiUrl: process.env.VITALSYNC_API_URL || 'http://vitalsync-api:8000'
    },

    // HTTP node settings
    httpRequestTimeout: 120000,

    // Context storage
    contextStorage: {
        default: {
            module: "memory"
        }
    },

    // Export global context on deploy
    exportGlobalContextKeys: false,

    // Deshabilitar runtime API (para producción)
    disableRuntimeApi: false,

    // HTTP admin root
    httpAdminRoot: '/',

    // HTTP node root
    httpNodeRoot: '/api',

    // CORS settings
    httpNodeCors: {
        origin: "*",
        methods: "GET,PUT,POST,DELETE"
    }
};
