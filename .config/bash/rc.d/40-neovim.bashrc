#!/usr/bin/env bash
#
__neovim_org_help() {
  cat <<EOF
Keymaps:
  format selection        gq gq
  format single line      gq gq
  format whole document   gg gq G

  org_agenda              <Leader>oa   g? for help.
  org_agenda_set_tags     <Leader>ot
  org_capture             <Leader>oc   Close with <C-c>.
  org_clock_cancel        <Leader>oxq
  org_clock_goto          <Leader>oxj
  org_clock_in            <Leader>oxi
  org_clock_out           <Leader>oxo
  org_move_subtree_down   <Leader>oJ
  org_move_subtree_up     <Leader>oK
  org_timestamp_down      <C-x>
  org_timestamp_down_day  <S-DOWN>
  org_timestamp_up        <C-a>
  org_timestamp_up_day    <S-UP>
  org_todo                cit          Cycle TODO keywords.
EOF
}
alias neovim-org-help='__neovim_org_help'

__main() {
  unset __main

  local opt_dir="${XDG_LOCAL_HOME:="${HOME}/.local"}/opt"
  local neovim_dir="${opt_dir}/neovim"
  local bin_dir="${neovim_dir}/bin"

  if [[ -x "${bin_dir}/nvim" ]]; then
    prepend_to_path_if_exists "${bin_dir}"
  fi
}

__main "$@"
