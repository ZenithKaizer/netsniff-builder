   HISTCONTROL=ignoreboth
PROMPT_COMMAND='history -a'
           PS1='\n\[\033[36m\]$(date +%-k:%M)\[\033[1;34m\]\u@\h:\w\[\033[0m\]$ '

alias ls='\ls -h --color=always'
alias ll='ls -l'
alias la='ls -la'
alias lt='ls -lt'

alias sedn='sedr -n'
alias sedr='sed  -r'
alias   vi='\vim -c "set number"'

alias vars='( set |sedr "/^[^ ]+ \(\)/q" ) | sedr "$ d; s/([^=]+)(=)/$C12\1$C14\2$C0/"'