# Designations
`To_sign_count` – the number of rounds for which the new separate state is created  
`last_round` - the id (round) after which the state was created   
`uncompressed_count` - the number of rounds, for which the order of transactions  
was found, but the state was not created yet  


# Description

### The creation of state

At the moment when the node obtained at least `To_sign_count` rounds where the final order of transactions was found, it generates the local balance of all known wallets (state) from the previous state and transactions which happened after that, during this the empty wallets are not saved.  
Also, whilst creation of state its hash is calculated in order to sent only it, but not the balance of all the wallets.
This state has the format dict `{address: amount}`. For the reason of hashes not to differ, we use `OrderedDict`. 
All transactions that were used to create the signed state are removed. As a result, we compress the transaction into one general balance and do not save their entire history.


### The sending of state to other nodes

Afterwards, when the state is created the data to send signature can be formed. In the current version, these data are the hash of state and `last_round`.
After that, we can sign them with our private key, create the transaction of type 1 and insert it into the pool.
In this case, when the new even is created, they will be insert into it and via the gossip protocol this event will be spread among other nodes, as well as the signature of the state.


### The handling of remote signatures

As soon as the node receives the new events, it tries immediately to find among them the transaction with the signature of the state.
After that, the validation occurs, and also it is checked whether it is our own transaction.
If the validation was successful, then the signature is inserted into database as non-verified.
This means, that its hash was not compared with our local ones.
Afterwards, since the remote signatures were updated, we try to sign our local state.


### The signing of local state

All non-verified remote signatures are taken from the database, and for each signature the hash is compared with locally created one.
If the hashes are the same, then the signature is inserted into the database as verified and it can be used further to count the collected signatures, or to be sent outside.
After the check, all non-verified signatures are removed, therefore, the signatures with incorrect (non-valid) hash are dropped.
Afterwards, the number of just added signatures is counted and also of those, that were in the database before (the verified one). If there is enough such signatures, then the state is signed. Therefore, we can clear the data, that were necessary to create this state, and the database is cleared. Therefore, we avoid storing of a large number of data


# Detailed technical part 

### Send signatures

1. Every time when the final order of transaction was found we take it into account and increment the `uncompressed_count` variable. 
2. Later, when we handle remote events, while `uncompressed_count` is greater or equal to the predefined size of packet `to_sign_count`,   
    we sign our local state and insert it into transaction and then to tx pool.  
	**Sign steps:**
	1. Get from database the rounds, for which the order of transaction was found, that are greater than the round for which   
	    we have already created the signatures (`last_created_sign`). In this case we take only `to_sign_count` documents.  
	2. Check whether the state of the last round taken from the databse is created, or create it, otherwise.    
	For this, the balance of wallets from the previous state is counted, and also the transactions, which occurred after it.   
    The wallets with zero balance are not included into the state.  
	3. Hashify the state with blake2 hash.  
	4. Create the `data` dictionary that will store values we need to handle in remote node.  
		The dictionary `data` contains:
		* `Hash` created at step 3.  It will be used by remote node to check whether the transactions order and state is the same or not.
		* `last_round`. This is the id (round), after which the state was created	
	5. Digitally sign ‘data’ dictionary with our private key.  
	6. Format appropriate type of transaction(for now it is type 1).  
	7. Insert the transaction into the list.   
3. If the event was successfully created, we decrease `uncompressed_count` and set new `last_created` round in the database. 
4. The signatures list was created after the previous steps, so we can insert them into the transaction pool.    
	
### Handle remote signatures  
After the determination of the final order of transactions, they are handled in `insert_processed_transaction`   
at `transaction.py`. (signatures are transmitted in transactions)  
1. Loop through all transactions in remote events and if transaction is a state signature,   
    insert it as unchecked into db (that means that we have not compared this remote hash with our local).  
2. Check if there are enough local rounds, for which the final order of transactions is found. 
    On success, sign as many states as we can.   
    Pay attention that we start signing from `last_signed_state`.  
	**Sign steps:**
    1. Get signatures to consensus packet that starts with the value greater than 'last_signed_con'.
    2. Compare every `unchecked_pair` hash with local consensus hash, if they are equal then insert as checked.
    3. Delete all unchecked pairs. We can do that because all valid signs are already stored.
    4. Calculate total count of valid signatures. If there are enough signatures, set sign flag to true in state database.
3. Clean the database, so there will never be a huge number of data stored.

## Questions
* **Why we use only `last_round` value ?**
    
From hashgraph docs: 
>>>
    Once consensus has been reached on whether each witness in round r is famous
    or not, a total order can be calculated for every event in history with a received
    round of r or less. It is also guaranteed that all other events (including any that
    are still unknown) will have a received round greater than r. In other words,
    at this point, history is frozen and immutable for all events up to round r.  
>>>
To be more precise, I call this round r as last_round

---

* **When and why we use clear parent option in `get_event` ?**  
After signing events we clean the database to avoid storing a huge number of data, 
so some events will be deleted too. However, some algorithms go through 
event parents recursively before they find root event (without parents), 
but at a certain period of time they will handle event that was already deleted. 
One way is to set new "root event" by removing parents, but in that case 
the hash of this event will change and it will not pass validation. 
As a result, we check if parent event was signed and remove it only for these algorithms.

