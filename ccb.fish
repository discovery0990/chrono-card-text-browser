function ccb --description "Live rg content search over card files"
    argparse 'g/glob=' 'd/dir=' -- $argv; or return
    set -l dir cards
    set -q _flag_dir; and set dir $_flag_dir
    set -l rgcmd "rg -il"
    if set -q _flag_glob
        string match -q '*/*' -- $_flag_glob
        and set _flag_glob $dir/$_flag_glob
        set rgcmd "$rgcmd -g "(string escape -- $_flag_glob)
    end
    fzf --disabled --query "$argv" \
        --bind "start:reload:$rgcmd -- {q} $dir | sort" \
        --bind "change:reload:$rgcmd -- {q} $dir | sort" \
        --bind "enter:ignore" \
        --preview 'rg -i --passthru --color=always -- {q} {}' \
        --preview-window 'right:70%:wrap'
    or test $status -eq 130
end
