# os_x_keychain_create_pipe_in_password

OS X has no ability to programmatically add to the keychain without leaking it to the process list, this is meant to do that.

Example usage:

echo "my_password" | python add_generic_password.py account_name service_name # creates new password
