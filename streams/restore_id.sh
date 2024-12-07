#!/bin/bash

vm_id=$1

C='\033[0;94m'
G='\033[0;32m'
L='\033[38;5;135m'
R='\033[91m'
NC='\033[0m'

if [[ $(df -T / | awk 'NR==2 {print $2}') == "zfs" ]]
	then
        dump_dir="/var/lib/vz/dump"
	else
        dump_dir="/var/lib/pve/local-btrfs/dump"
fi 

# Überprüfen, ob das Argument gesetzt ist
if [ -z "$vm_id" ]; then
    echo -e "${R}Error: VM_ID was left empty!${NC}"
    exit 1
fi

## Wenn die VM vor dem Restore zerstört werden soll, hier die Kommentierungen entfernen:
# echo -e "${C}Destroying VM${NC}"
sudo qm stop $vm_id
# sudo qm destroy $vm_id

# Überprüfen, ob das Verzeichnis existiert
if [ ! -d "$dump_dir" ]; then
    echo -e "${R}Error: Directory $dump_dir does not exist.${NC}"
    exit 1
fi

# Durchlaufen aller .vma-Dateien im Verzeichnis
for vma_file in "$dump_dir"/*.vma; 
    do
    # VMID aus dem Dateinamen extrahieren
    vmid=$(basename "$vma_file" | grep -oP '(?<=vzdump-qemu-)\d+')

    # Überprüfen, ob die VMID extrahiert wurde
    if [ -z "$vmid" ]; then
        echo -e "${R}Error: Could not extract VMID from $vma_file.${NC}"
        exit 1
    fi

    # Prüfen, ob es sich um die VMID handelt
    if [[ "$vmid" == "$vm_id" ]]; then
        echo -e "${C}Restoring VM $vmid ...${NC}"
        sudo qmrestore "$vma_file" "$vmid" --force
    fi
    done

echo -e "${C}Starting VM $vm_id and updating SSH known hosts${NC}"
    sudo qm start "$vm_id"
    ssh-keygen -f "${HOME}/.ssh/known_hosts" -R ""

echo -e "${G}Restore of VM ${L}$vm_id${G} executed successfully!${NC}"
