if !has('nvim')
  finish
endif

try
  lua require('codecompanion')
catch /^Vim\%((\a\+)\)\=:E5108:/
  finish
endtry

lua << EOF
codecompanion_setup = {
  adapters = {
    acp = {
      opts = {
        show_presets = false,
      },
    },
    http = {
      opts = {
        show_model_choices = false,
        show_presets = false,
      },
      ["openrouter_xxxx"] = function()
        return require("codecompanion.adapters").extend("openai_compatible", {
          env = {
            url = "https://openrouter.ai/api",
            api_key = "sk-or-v1-                                                                ",
            chat_url = "/v1/chat/completions",
          },
          schema = {
            model = {
              -- default = "minimax/minimax-m2.5:free",
              default = "openai/gpt-oss-120b:free",
            },
          },
        })
      end,
    },
  },
  interactions = {
    chat = {
      adapter = "openrouter_xxxx",
    },
  },
  opts = {
    log_level = "DEBUG", -- or "TRACE"
  }
}
EOF
