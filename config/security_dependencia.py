from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Depends
from config.security import get_current_user, get_admin_user

OAuth2FormDeDependencia = Annotated[OAuth2PasswordRequestForm, Depends()]
#estaba como strng pero lo pase a dict
Token_Dependencia = Annotated[dict, Depends(get_current_user)]
Admin_Token_Dependencia = Annotated[dict, Depends(get_admin_user)]

