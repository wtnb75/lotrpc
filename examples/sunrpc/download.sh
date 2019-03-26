#! /bin/sh

baseurl="https://sourceware.org/git/?p=glibc.git;a=blob_plain;f=sunrpc/rpcsvc/"

for i in bootparam_prot key_prot klm_prot mount nfs_prot nlm_prot rex rquota rstat rusers sm_inter spray yppasswd; do
  curl -LO ${baseurl}${i}.x
done

