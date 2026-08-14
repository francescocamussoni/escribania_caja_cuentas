from pydantic import BaseModel, ConfigDict, Field, model_validator


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    rol: str


class _ChangePasswordBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    new_password_confirm: str = Field(min_length=8)

    @model_validator(mode="after")
    def confirm_matches_new_password(self) -> "_ChangePasswordBase":
        if self.new_password != self.new_password_confirm:
            raise ValueError("La confirmación no coincide con la nueva contraseña")
        return self


class ChangePasswordPublicRequest(_ChangePasswordBase):
    username: str = Field(min_length=1, max_length=50)


class ChangePasswordAuthenticatedRequest(_ChangePasswordBase):
    pass
